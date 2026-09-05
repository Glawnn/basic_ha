"""Example buttons: generic command publish.

Repris de pc-ha/button.py — 1 bouton qui publie sur basic-ha/<id>/command.
"""

from __future__ import annotations

import json

from homeassistant.components import mqtt
from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, TOPIC_COMMAND
from .coordinator import BasicHaCoordinator
from .sensor import device_info


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: BasicHaCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    def entities_for(device_id: str) -> list[ButtonEntity]:
        return [BasicHaCommandButton(coordinator, device_id, "ping")]

    async_add_entities([e for dev in coordinator.data for e in entities_for(dev)])

    @callback
    def add_new_device(device_id: str) -> None:
        async_add_entities(entities_for(device_id))

    hass.data[DOMAIN][entry.entry_id]["new_device_callbacks"].append(add_new_device)


class BasicHaCommandButton(CoordinatorEntity[BasicHaCoordinator], ButtonEntity):
    """Bouton générique — publie {"action": ...} sur le topic command."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: BasicHaCoordinator, device_id: str, action: str) -> None:
        super().__init__(coordinator)
        self._device_id = device_id
        self._action = action
        self._attr_unique_id = f"{device_id}_{action}"
        self._attr_translation_key = action
        self._attr_device_info = device_info(device_id)

    @property
    def available(self) -> bool:
        # Exemple: bouton dispo seulement si device online
        return super().available and self.coordinator.data.get(self._device_id, {}).get(
            "available", False
        )

    async def async_press(self) -> None:
        await mqtt.async_publish(
            self.hass,
            TOPIC_COMMAND.format(device_id=self._device_id),
            json.dumps({"action": self._action}),
            qos=1,
            retain=False,
        )
