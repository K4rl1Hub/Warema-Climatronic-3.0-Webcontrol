from __future__ import annotations
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from . import DOMAIN

class WebControlBinarySensorSommerWinter(BinarySensorEntity):
    _attr_device_class = "cold"  # winter aktiv => kalt

    def __init__(self, client):
        self._client = client
        self._attr_name = "Sommer/Winter aktiv"
        self._attr_unique_id = "webcontrol_binary_sommer_winter"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, "webcontrol")}, name="Warema WebControl")

    @property
    def is_on(self):
        # Winter aktiv == 1
        return bool(self._client.sommer_winter_aktiv == 1)


def setup_platform(hass: HomeAssistant, config, add_entities, discovery_info=None):
    client = hass.data[DOMAIN]["client"]
    add_entities([WebControlBinarySensorSommerWinter(client)], True)
