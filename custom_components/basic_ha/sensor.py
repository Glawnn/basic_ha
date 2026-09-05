"""Example sensors: one value sensor per device_id.

Pattern repris de pc-ha/sensor.py — adapte les clés selon ton payload MQTT.
"""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import BasicHaCoordinator


def device_info(device_id: str) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, device_id)},
        name=device_id,
        manufacturer="basic_ha",
        model="MQTT Device",
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: BasicHaCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    def entities_for(device_id: str) -> list[SensorEntity]:
        return [BasicHaValueSensor(coordinator, device_id)]

    async_add_entities([e for dev in coordinator.data for e in entities_for(dev)])

    @callback
    def add_new_device(device_id: str) -> None:
        async_add_entities(entities_for(device_id))

    hass.data[DOMAIN][entry.entry_id]["new_device_callbacks"].append(add_new_device)


class BasicHaValueSensor(CoordinatorEntity[BasicHaCoordinator], SensorEntity):
    """Exemple: lit `value` du payload JSON `basic-ha/<id>/state`."""

    _attr_has_entity_name = True
    _attr_translation_key = "value"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: BasicHaCoordinator, device_id: str) -> None:
        super().__init__(coordinator)
        self._device_id = device_id
        self._attr_unique_id = f"{device_id}_value"
        self._attr_device_info = device_info(device_id)

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.data.get(self._device_id, {}).get(
            "available", False
        )

    @property
    def native_value(self) -> float | None:
        v = self.coordinator.data.get(self._device_id, {}).get("value")
        # TODO: adapte la clé / le type selon ton payload
        try:
            return float(v) if v is not None else None
        except (TypeError, ValueError):
            return None
