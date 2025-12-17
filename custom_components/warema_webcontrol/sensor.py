from __future__ import annotations
from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from . import DOMAIN

LANG_MAP = {
    0: "Deutsch",
    1: "Englisch",
    2: "Französisch",
    3: "Italienisch",
    4: "Spanisch",
}

class WebControlLanguageSensor(SensorEntity):
    _attr_icon = "mdi:translate"

    def __init__(self, client):
        self._client = client
        self._attr_name = "WebControl Sprache"
        self._attr_unique_id = "webcontrol_language"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, "webcontrol")}, name="Warema WebControl")

    @property
    def native_value(self):
        code = self._client.language
        return LANG_MAP.get(code, f"Code {code}")

    @property
    def extra_state_attributes(self):
        return {"code": self._client.language, "base_url": self._client.base_url}


def setup_platform(hass: HomeAssistant, config, add_entities, discovery_info=None):
    client = hass.data[DOMAIN]["client"]
    add_entities([WebControlLanguageSensor(client)], True)
