from __future__ import annotations
from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from . import DOMAIN

class WebControlSwitchAbwesend(SwitchEntity):
    def __init__(self, client):
        self._client = client
        self._state = bool(client.abwesend) if client.abwesend is not None else False
        self._attr_name = "Abwesend"
        self._attr_unique_id = "webcontrol_switch_abwesend"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, "webcontrol")}, name="Warema WebControl")

    @property
    def is_on(self):
        return self._state

    def turn_on(self, **kwargs):
        res = self._client.set_abwesend(True)
        self._state = True if res is not None else self._state
        self.schedule_update_ha_state()

    def turn_off(self, **kwargs):
        res = self._client.set_abwesend(False)
        self._state = False if res is not None else self._state
        self.schedule_update_ha_state()


class WebControlSwitchAutomatik(SwitchEntity):
    def __init__(self, client):
        self._client = client
        self._state = bool(client.automatik) if client.automatik is not None else False
        self._attr_name = "Automatik"
        self._attr_unique_id = "webcontrol_switch_automatik"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, "webcontrol")}, name="Warema WebControl")

    @property
    def is_on(self):
        return self._state

    def turn_on(self, **kwargs):
        res = self._client.set_automatik(True)
        self._state = True if res is not None else self._state
        self.schedule_update_ha_state()

    def turn_off(self, **kwargs):
        res = self._client.set_automatik(False)
        self._state = False if res is not None else self._state
        self.schedule_update_ha_state()


def setup_platform(hass: HomeAssistant, config, add_entities, discovery_info=None):
    data = hass.data[DOMAIN]
    client = data["client"]
    add_entities([WebControlSwitchAbwesend(client), WebControlSwitchAutomatik(client)], True)
