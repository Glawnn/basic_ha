"""Binary sensor: online/offline via availability (LWT)."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import BasicHaCoordinator
from .sensor import device_info


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: BasicHaCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    async_add_entities(
        BasicHaOnlineSensor(coordinator, dev) for dev in coordinator.data
    )

    @callback
    def add_new_device(device_id: str) -> None:
        async_add_entities([BasicHaOnlineSensor(coordinator, device_id)])

    hass.data[DOMAIN][entry.entry_id]["new_device_callbacks"].append(add_new_device)


class BasicHaOnlineSensor(CoordinatorEntity[BasicHaCoordinator], BinarySensorEntity):
    """`on` = online, `off` = offline. Jamais `unavailable`."""

    _attr_has_entity_name = True
    _attr_translation_key = "online"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, coordinator: BasicHaCoordinator, device_id: str) -> None:
        super().__init__(coordinator)
        self._device_id = device_id
        self._attr_unique_id = f"{device_id}_online"
        self._attr_device_info = device_info(device_id)

    @property
    def is_on(self) -> bool:
        return bool(
            self.coordinator.data.get(self._device_id, {}).get("available", False)
        )

    @property
    def available(self) -> bool:
        return super().available
