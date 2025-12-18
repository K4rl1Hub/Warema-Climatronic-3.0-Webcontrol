from __future__ import annotations
from homeassistant.components.light import LightEntity, ColorMode
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DOMAIN

class WebControlLight(CoordinatorEntity, LightEntity):
    _attr_should_poll = False
    _attr_supported_color_modes = {ColorMode.ONOFF}
    _attr_color_mode = ColorMode.ONOFF

    def __init__(self, hass: HomeAssistant, client, coordinator, ch):
        super().__init__(coordinator)
        self._client = client
        self._ch = ch
        self._attr_name = ch.name or f"Licht {ch.cli_index}"
        self._attr_unique_id = f"webcontrol_light_{ch.cli_index}"
        self._is_on = False
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, "webcontrol")}, name="Warema WebControl"
        )

    def turn_on(self, **kwargs):
        self._client.light_on(self._ch)
        self._is_on = True

    def turn_off(self, **kwargs):
        self._client.light_off(self._ch)
        self._is_on = False

    @property
    def is_on(self):
        data = self.coordinator.data or {}
        key = (self._ch.raumindex, self._ch.kanalindex)
        st = data.get(key)
        if st and st.get("lastp") is not None:
            self._is_on = (st["lastp"] >= 200)
        return self._is_on



async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    data = hass.data[DOMAIN]
    client = data["client"]
    coordinator = data["coordinator"]
    lights = data["mapped"]["light"]
    entities = [WebControlLight(hass, client, coordinator, ch) for ch in lights]
    async_add_entities(entities)

