from __future__ import annotations
from homeassistant.components.light import LightEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from . import DOMAIN

class WebControlLight(LightEntity):
    def __init__(self, client, ch):
        self._client = client
        self._ch = ch
        self._attr_name = ch.name or f"Licht {ch.cli_index}"
        self._attr_unique_id = f"webcontrol_light_{ch.cli_index}"
        self._is_on = False
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, "webcontrol")}, name="Warema WebControl"
        )

    def turn_on(self, **kwargs):
        self._client.light_on(self._ch.raumindex, self._ch.kanalindex)
        self._is_on = True

    def turn_off(self, **kwargs):
        self._client.light_off(self._ch.raumindex, self._ch.kanalindex)
        self._is_on = False

    @property
    def is_on(self):
        return self._is_on


def setup_platform(hass: HomeAssistant, config, add_entities, discovery_info=None):
    data = hass.data[DOMAIN]
    client = data["client"]
    lights = data["mapped"]["light"]
    entities = [WebControlLight(client, ch) for ch in lights]
    add_entities(entities, True)
