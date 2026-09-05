"""Basic HA integration — 1 device per MQTT device_id, fed by MQTT."""

from __future__ import annotations

import json
import logging

from homeassistant.components import mqtt
from homeassistant.components.mqtt.models import ReceiveMessage
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN, PLATFORMS, TOPIC_AVAILABILITY, TOPIC_RESULT, TOPIC_STATE
from .coordinator import BasicHaCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Subscribe to basic-ha topics and forward platforms."""
    if not await mqtt.async_wait_for_mqtt_client(hass):
        raise ConfigEntryNotReady("MQTT client not available")

    coordinator = BasicHaCoordinator(hass, entry)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "coordinator": coordinator,
        "new_device_callbacks": [],
    }

    def notify_new_device(device_id: str) -> None:
        for cb in hass.data[DOMAIN][entry.entry_id]["new_device_callbacks"]:
            cb(device_id)

    @callback
    def state_received(msg: ReceiveMessage) -> None:
        try:
            device_id = msg.topic.split("/")[1]
        except IndexError:
            _LOGGER.warning("Ignoring malformed topic: %s", msg.topic)
            return
        try:
            payload = json.loads(msg.payload)
        except ValueError:
            _LOGGER.warning("Ignoring non-JSON payload on %s", msg.topic)
            return
        if coordinator.handle_state(device_id, payload):
            _LOGGER.debug("New device discovered: %s", device_id)
            notify_new_device(device_id)

    @callback
    def availability_received(msg: ReceiveMessage) -> None:
        try:
            device_id = msg.topic.split("/")[1]
        except IndexError:
            return
        online = msg.payload.strip().lower() == "online"
        if coordinator.handle_availability(device_id, online):
            notify_new_device(device_id)

    @callback
    def result_received(msg: ReceiveMessage) -> None:
        try:
            device_id = msg.topic.split("/")[1]
        except IndexError:
            return
        try:
            payload = json.loads(msg.payload)
        except ValueError:
            return
        coordinator.handle_result(device_id, payload)

    unsub_state = await mqtt.async_subscribe(hass, TOPIC_STATE, state_received, qos=1)
    unsub_avail = await mqtt.async_subscribe(
        hass, TOPIC_AVAILABILITY, availability_received, qos=1
    )
    unsub_result = await mqtt.async_subscribe(
        hass, TOPIC_RESULT, result_received, qos=1
    )
    hass.data[DOMAIN][entry.entry_id]["unsubs"] = [
        unsub_state,
        unsub_avail,
        unsub_result,
    ]

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unsubscribe and unload platforms."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    for unsub in hass.data.get(DOMAIN, {}).get(entry.entry_id, {}).get("unsubs", []):
        unsub()
    hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return unload_ok
