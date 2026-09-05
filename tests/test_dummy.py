"""Dummy tests — validate the template without requiring a full HA run.

These tests are intentionally simple but catch real breakage:
- manifest/hacs json are valid
- constants match integration domain
- coordinator merges state correctly (core logic from pc-ha)
"""

from __future__ import annotations

import json
import pathlib
import re
from unittest.mock import MagicMock

ROOT = pathlib.Path(__file__).parent.parent


def test_manifest_valid():
    manifest = json.loads((ROOT / "custom_components/basic_ha/manifest.json").read_text())
    assert manifest["domain"] == "basic_ha"
    assert manifest["config_flow"] is True
    assert "mqtt" in manifest["dependencies"]
    # version must be semver 0.1.0 style
    assert re.match(r"^\d+\.\d+\.\d+$", manifest["version"])


def test_hacs_json_valid():
    hacs = json.loads((ROOT / "hacs.json").read_text())
    assert hacs["name"] == "Basic HA"
    assert "homeassistant" in hacs


def test_const_topics():
    from custom_components.basic_ha.const import DOMAIN, PLATFORMS, TOPIC_STATE

    assert DOMAIN == "basic_ha"
    assert len(PLATFORMS) >= 1
    assert "basic-ha" in TOPIC_STATE
    assert TOPIC_STATE == "basic-ha/+/state"


def test_coordinator_merge_state():
    """Coordinator merges payloads and reports is_new correctly."""
    from custom_components.basic_ha.coordinator import BasicHaCoordinator

    # Minimal mock hass + entry — coordinator only needs them for __init__
    hass = MagicMock()
    entry = MagicMock()
    entry.entry_id = "test"

    coord = BasicHaCoordinator(hass, entry)
    # Avoid calling async_set_updated_data which needs HA loop — patch it
    coord.async_set_updated_data = MagicMock()

    # First state for demo -> new
    is_new = coord.handle_state("demo", {"value": 42})
    assert is_new is True
    assert coord.data["demo"]["value"] == 42
    assert coord.data["demo"]["available"] is True

    # Second state for same demo -> not new, merges
    is_new = coord.handle_state("demo", {"value": 43, "extra": "x"})
    assert is_new is False
    assert coord.data["demo"]["value"] == 43
    assert coord.data["demo"]["extra"] == "x"

    # Availability
    is_new_avail = coord.handle_availability("demo", False)
    assert is_new_avail is False
    assert coord.data["demo"]["available"] is False

    is_new_avail2 = coord.handle_availability("new_device", True)
    assert is_new_avail2 is True


def test_strings_translations_present():
    strings = json.loads((ROOT / "custom_components/basic_ha/strings.json").read_text())
    assert "config" in strings
    assert "entity" in strings
    en = json.loads((ROOT / "custom_components/basic_ha/translations/en.json").read_text())
    fr = json.loads((ROOT / "custom_components/basic_ha/translations/fr.json").read_text())
    assert en["entity"]["sensor"]["value"]["name"] == "Value"
    assert fr["entity"]["sensor"]["value"]["name"] == "Valeur"
