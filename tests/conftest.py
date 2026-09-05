"""Fixtures for basic_ha tests."""

from __future__ import annotations

import sys
import types

import pytest

# Mock minimal homeassistant modules if HA not installed
try:
    import homeassistant  # noqa: F401

    HAS_HA = True
except ImportError:  # pragma: no cover
    HAS_HA = False

    def _ensure_module(name: str, is_package: bool = False) -> types.ModuleType:
        if name not in sys.modules:
            mod = types.ModuleType(name)
            if is_package:
                mod.__path__ = []  # type: ignore
            sys.modules[name] = mod
        return sys.modules[name]

    # Create package hierarchy
    ha = _ensure_module("homeassistant", True)
    ha_const = _ensure_module("homeassistant.const")
    ha_components = _ensure_module("homeassistant.components", True)
    ha_mqtt = _ensure_module("homeassistant.components.mqtt", True)
    ha_mqtt_models = _ensure_module("homeassistant.components.mqtt.models")
    ha_sensor = _ensure_module("homeassistant.components.sensor")
    ha_binary = _ensure_module("homeassistant.components.binary_sensor")
    ha_button = _ensure_module("homeassistant.components.button")
    ha_config = _ensure_module("homeassistant.config_entries")
    ha_core = _ensure_module("homeassistant.core")
    ha_exc = _ensure_module("homeassistant.exceptions")
    ha_helpers = _ensure_module("homeassistant.helpers", True)
    ha_entity = _ensure_module("homeassistant.helpers.entity")
    ha_platform = _ensure_module("homeassistant.helpers.entity_platform")
    ha_coord = _ensure_module("homeassistant.helpers.update_coordinator")

    # Link parents to children (so import finds submodule via attribute)
    ha.helpers = ha_helpers
    ha_components.mqtt = ha_mqtt
    ha_mqtt.models = ha_mqtt_models
    ha_helpers.entity = ha_entity
    ha_helpers.entity_platform = ha_platform
    ha_helpers.update_coordinator = ha_coord
    ha.const = ha_const
    ha.components = ha_components
    ha.config_entries = ha_config
    ha.core = ha_core
    ha.exceptions = ha_exc

    # stubs
    from enum import Enum

    class Platform(str, Enum):
        SENSOR = "sensor"
        BINARY_SENSOR = "binary_sensor"
        BUTTON = "button"

    ha_const.Platform = Platform

    class _Duc:
        def __init__(self, *a, **kw):
            self.data = {}
            self.logger = kw.get("logger")

        def async_set_updated_data(self, data):
            self.data = data

        def __class_getitem__(cls, item):
            return cls

    ha_coord.DataUpdateCoordinator = _Duc
    ha_core.callback = lambda f: f

    class ReceiveMessage:
        topic: str
        payload: str

    ha_mqtt_models.ReceiveMessage = ReceiveMessage

    async def _async_subscribe(*a, **kw):
        return lambda: None

    ha_mqtt.async_subscribe = _async_subscribe
    ha_mqtt.async_publish = _async_subscribe
    ha_mqtt.async_wait_for_mqtt_client = _async_subscribe

    # minimal ConfigEntry / HomeAssistant / exception stubs
    ha_config.ConfigEntry = type("ConfigEntry", (), {})
    ha_core.HomeAssistant = type("HomeAssistant", (), {})
    ha_exc.ConfigEntryNotReady = type("ConfigEntryNotReady", (Exception,), {})

try:
    from pytest_homeassistant_custom_component.common import MockConfigEntry  # noqa: F401

    HAS_HA = HAS_HA and True
except Exception:  # noqa: S110  # pragma: no cover
    pass


@pytest.fixture
def enable_custom_integrations():
    """Enable custom integrations for HA tests (required by PHAC)."""
    return True
