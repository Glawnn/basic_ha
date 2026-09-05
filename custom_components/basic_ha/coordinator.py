"""Push coordinator: MQTT callbacks feed per-device state, entities read from it.

Inspiré de pc-ha/coordinator.py — DataUpdateCoordinator sans polling.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


class BasicHaCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    """Holds the latest state per device_id. No polling — MQTT pushes updates."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name="basic_ha",
            update_interval=None,
        )
        self.data: dict[str, dict[str, Any]] = {}

    @callback
    def handle_state(self, device_id: str, payload: dict[str, Any]) -> bool:
        """Merge a state payload. Returns True when this device_id is new."""
        previous = self.data.get(device_id, {})
        is_new = device_id not in self.data
        self.data[device_id] = {
            **previous,
            **payload,
            "available": previous.get("available", True),
        }
        self.async_set_updated_data(self.data)
        return is_new

    @callback
    def handle_availability(self, device_id: str, online: bool) -> bool:
        """Merge an availability message. Returns True when device_id is new."""
        is_new = device_id not in self.data
        entry = self.data.get(device_id, {})
        entry["available"] = online
        self.data[device_id] = entry
        self.async_set_updated_data(self.data)
        return is_new

    @callback
    def handle_result(self, device_id: str, payload: dict[str, Any]) -> None:
        """Store the last command ack per device (debug/audit)."""
        entry = self.data.get(device_id, {})
        entry["last_result"] = payload
        self.data[device_id] = entry
        self.async_set_updated_data(self.data)
        _LOGGER.info(
            "Command result for %s: %s (%s)",
            device_id,
            payload.get("action"),
            payload.get("status"),
        )
