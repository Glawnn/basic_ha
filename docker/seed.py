#!/usr/bin/env python3
"""Seed the clean HA dev env via its HTTP API (idempotent, stdlib only).

Does, in order:
  1. Wait for HA to answer.
  2. If onboarding is pending: create the owner account (HA_USERNAME/HA_PASSWORD)
     and complete the remaining steps (core_config, analytics, integration).
  3. Log in (login_flow -> auth_code -> token).
  4. Create the MQTT config entry (BROKER_HOST:BROKER_PORT) if absent.

Everything persists in the `ha_config` volume, so re-running is a fast no-op.
Exit 0 on success (already-seeded or freshly seeded), non-zero on failure.

Env (all optional):
  HA_URL        default http://localhost:8123 (from compose network: http://homeassistant:8123)
  HA_USERNAME   default test
  HA_PASSWORD   default test
  HA_NAME       default Test
  HA_LANGUAGE   default fr
  BROKER_HOST   default mosquitto
  BROKER_PORT   default 1883
  BROKER_USER   default "" (anonymous; set for authenticated brokers)
  BROKER_PASS   default "" (anonymous; set for authenticated brokers)
"""

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

HA_URL = os.environ.get("HA_URL", "http://localhost:8123").rstrip("/")
USERNAME = os.environ.get("HA_USERNAME", "test")
PASSWORD = os.environ.get("HA_PASSWORD", "test")
NAME = os.environ.get("HA_NAME", "Test")
LANGUAGE = os.environ.get("HA_LANGUAGE", "fr")
BROKER_HOST = os.environ.get("BROKER_HOST", "mosquitto")
BROKER_PORT = int(os.environ.get("BROKER_PORT", "1883"))
# Optional MQTT credentials for the HA broker entry (dual-auth brokers accept
# both anonymous and authenticated clients; leave empty for anonymous).
BROKER_USER = os.environ.get("BROKER_USER", "")
BROKER_PASS = os.environ.get("BROKER_PASS", "")
CLIENT_ID = HA_URL + "/"


def req(method, path, data=None, token=None):
    body = json.dumps(data).encode() if data is not None else None
    r = urllib.request.Request(
        HA_URL + path, data=body, method=method,
        headers={"Content-Type": "application/json"},
    )
    if token:
        r.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(r, timeout=10) as resp:
            return resp.status, json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode() or "{}")
        except Exception:
            return e.code, {}


def form(path, fields):
    """POST application/x-www-form-urlencoded (used by /auth/token)."""
    body = urllib.parse.urlencode(fields).encode()
    r = urllib.request.Request(
        HA_URL + path, data=body, method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(r, timeout=10) as resp:
        return json.loads(resp.read().decode())


def log(msg):
    print(msg, flush=True)


def main():
    log(f"==> Waiting for HA at {HA_URL} ...")
    for _ in range(90):
        try:
            with urllib.request.urlopen(HA_URL + "/api/", timeout=5) as resp:
                code = resp.status
        except urllib.error.HTTPError as e:
            code = e.code  # 401 = up, auth required
        except Exception:
            code = 0
        if code in (200, 401):
            break
        time.sleep(2)
    else:
        log("HA did not come up in time"); return 1

    # --- 1. Onboarding -----------------------------------------------------
    status, body = req("GET", "/api/onboarding")
    token = None
    if status == 404:
        log("Onboarding already complete.")
    elif status == 200:
        pending = [s["step"] for s in body if not s.get("done")]
        log(f"Onboarding pending steps: {pending}")
        if "user" in pending:
            log(f"==> Creating owner account '{USERNAME}' ...")
            status, body = req("POST", "/api/onboarding/users", {
                "name": NAME, "username": USERNAME, "password": PASSWORD,
                "language": LANGUAGE, "client_id": CLIENT_ID,
            })
            auth_code = body.get("auth_code", "")
            if not auth_code:
                log(f"User creation failed: {body}"); return 1
            token = form("/auth/token", {
                "grant_type": "authorization_code",
                "code": auth_code, "client_id": CLIENT_ID,
            })["access_token"]
            log("Owner account created.")
            # Refresh: user step is now done, complete whatever remains.
            status, body = req("GET", "/api/onboarding")
            pending = [s["step"] for s in body if not s.get("done")] \
                if status == 200 else []
        if token is None:
            token = login()
            if token is None:
                return 1
        payloads = {
            "core_config": {},
            "analytics": {},
            "integration": {"client_id": CLIENT_ID,
                            "redirect_uri": CLIENT_ID + "?auth_callback=1"},
        }
        for step in pending:
            status, body = req("POST", f"/api/onboarding/{step}",
                               payloads.get(step, {}), token)
            log(f"Onboarding step '{step}': HTTP {status}")
    else:
        log(f"Unexpected onboarding status: HTTP {status} {body}"); return 1

    # --- 2. Login (if we don't already hold a token) ------------------------
    if token is None:
        log(f"==> Logging in as {USERNAME} ...")
        token = login()
        if token is None:
            return 1

    # --- 3. MQTT entry (idempotent) ------------------------------------------
    status, entries = req("GET", "/api/config/config_entries/entry", None, token)
    existing = sum(1 for e in entries if e.get("domain") == "mqtt")
    if existing:
        log(f"MQTT already configured ({existing} entr(y/ies)), nothing to do.")
        return 0

    log(f"==> Creating MQTT entry ({BROKER_HOST}:{BROKER_PORT}) ...")
    status, flow = req("POST", "/api/config/config_entries/flow",
                       {"handler": "mqtt", "show_advanced_options": False}, token)
    flow_id = flow.get("flow_id", "")
    if not flow_id:
        log(f"MQTT flow init failed: {flow}"); return 1
    status, result = req("POST", f"/api/config/config_entries/flow/{flow_id}", {
        "broker": BROKER_HOST, "port": BROKER_PORT,
        **({"username": BROKER_USER, "password": BROKER_PASS} if BROKER_USER else {}),
        "other_settings": {"set_client_cert": False,
                           "set_ca_cert": "off", "transport": "tcp"},
    }, token)
    if result.get("type") == "create_entry" and result.get("result", {}).get("state") == "loaded":
        log("MQTT entry created and loaded.")
        return 0
    log(f"MQTT entry creation failed: {result}")
    return 1


def login():
    """login_flow (user/pass) -> auth_code -> access token. None on failure."""
    status, flow = req("POST", "/auth/login_flow", {
        "client_id": CLIENT_ID, "handler": ["homeassistant", None],
        "redirect_uri": CLIENT_ID + "?auth_callback=1",
    })
    flow_id = flow.get("flow_id", "")
    if not flow_id:
        log(f"Login flow init failed: {flow}"); return None
    status, done = req("POST", f"/auth/login_flow/{flow_id}", {
        "client_id": CLIENT_ID, "username": USERNAME, "password": PASSWORD,
    })
    code = done.get("result", "")
    if not code:
        log(f"Login failed (bad HA_USERNAME/HA_PASSWORD?): {done}"); return None
    try:
        return form("/auth/token", {
            "grant_type": "authorization_code",
            "code": code, "client_id": CLIENT_ID,
        })["access_token"]
    except Exception as e:
        log(f"Token exchange failed: {e}"); return None


if __name__ == "__main__":
    sys.exit(main())
