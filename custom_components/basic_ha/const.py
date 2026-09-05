"""Constants for Basic HA."""

from homeassistant.const import Platform

DOMAIN = "basic_ha"

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.BUTTON]

# Topics MQTT — adapte le préfixe si besoin
TOPIC_STATE = "basic-ha/+/state"
TOPIC_AVAILABILITY = "basic-ha/+/availability"
TOPIC_COMMAND = "basic-ha/{device_id}/command"
TOPIC_RESULT = "basic-ha/+/result"
