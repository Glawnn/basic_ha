# basic_ha — Template dev Home Assistant + MQTT

Template minimal prêt à coder, repris de `pc-ha` (sans Rust, sans `docs/`).

Chaque device publie sur `basic-ha/<id>/state` + `availability`, HA crée 1 appareil = 1 `device_id` avec capteurs/boutons.

## Prérequis

- Docker (WSL2 OK)
- Python 3

## Démarrage rapide

```bash
make env-up     # HA sur http://localhost:8123 + Mosquitto :1883 + seed auto
# ouvre http://localhost:8123  login test / test
# Paramètres → Appareils et services → Ajouter intégration → Basic HA
```

Publie un état test :

```bash
docker exec basic-ha-mosquitto mosquitto_pub -h localhost -p 1883 \
  -t 'basic-ha/demo/state' -q 1 -r -m '{"value": 42}'
docker exec basic-ha-mosquitto mosquitto_pub -h localhost -p 1883 \
  -t 'basic-ha/demo/availability' -q 1 -r -m 'online'
# -> Appareil `demo` apparaît avec sensor Value=42, binary_sensor Online=on, bouton Ping
```

```bash
make logs        # tout
make logs-ha     # HA
make logs-mqtt   # Mosquitto
make env-down    # stop (volumes gardés)
make env-clean   # reset total (re-seed au prochain up)
docker exec basic-ha-mosquitto mosquitto_sub -h localhost -p 1883 -t 'basic-ha/#' -v
```

## Layout

```
basic_ha/
├── Makefile
├── hacs.json
├── docker/
│   ├── compose.yaml            # homeassistant + mosquitto + seed
│   ├── ha_config/configuration.yaml
│   ├── mosquitto/mosquitto.conf + passwd (test/test)
│   └── seed.py                 # onboarding + entrée MQTT
└── custom_components/basic_ha/
    ├── manifest.json           # dependencies: ["mqtt"]
    ├── const.py                # topics
    ├── __init__.py             # subscriptions MQTT
    ├── coordinator.py          # push, data[device_id]
    ├── config_flow.py          # entrée unique
    ├── sensor.py / binary_sensor.py / button.py  # 1 exemple chacun
    └── translations/en.json + fr.json
```

## Renommer

Cherche/remplace `basic_ha` + `basic-ha` + `Basic HA` vers ton nouveau domaine. Garde `hacs.json` aligné avec `manifest.json`.

## Protocole MQTT (QoS 1)

| Topic | Sens | Retain | Payload |
|---|---|---|---|
| `basic-ha/<id>/state` | device → HA | ✅ | `{"value": 42, ...}` (JSON libre) |
| `basic-ha/<id>/availability` | device → HA | ✅ | `online` / `offline` (LWT) |
| `basic-ha/<id>/command` | HA → device | ❌ | `{"action":"ping"}` |
| `basic-ha/<id>/result` | device → HA | ❌ | `{"action","status","message"}` |

`command` jamais retained (sinon rejoué au reconnect).
