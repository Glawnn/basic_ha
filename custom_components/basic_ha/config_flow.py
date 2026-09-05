"""Config flow: single entry, MQTT broker is configured separately."""

from __future__ import annotations

from homeassistant import config_entries
from homeassistant.components import mqtt

from .const import DOMAIN


class BasicHaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")
        if not await mqtt.async_wait_for_mqtt_client(self.hass):
            return self.async_abort(reason="mqtt_not_setup")
        return self.async_create_entry(title="Basic HA", data={})
