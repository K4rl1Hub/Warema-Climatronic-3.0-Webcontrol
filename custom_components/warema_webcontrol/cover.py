from __future__ import annotations
from homeassistant.components.cover import CoverEntity, CoverEntityFeature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DOMAIN

class WebControlCover(CoordinatorEntity, CoverEntity):
    _attr_supported_features = (
        CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE |
        CoverEntityFeature.STOP | CoverEntityFeature.SET_POSITION
    )
    _attr_should_poll = False

    def __init__(self, hass: HomeAssistant, client, coordinator, ch):
        super().__init__(coordinator)
        self._client = client
        self._ch = ch
        self._attr_name = ch.name or f"Rollladen {ch.cli_index}"
        self._attr_unique_id = f"webcontrol_cover_{ch.cli_index}"
        self._position = None
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, "webcontrol")}, name="Warema WebControl"
        )
        self._last_cause = None  # cliausl Code

    def open_cover(self, **kwargs):
        self._client.cover_open(self._ch)

    def close_cover(self, **kwargs):
        self._client.cover_close(self._ch)

    def stop_cover(self, **kwargs):
        self._client.cover_stop(self._ch)

    def set_cover_position(self, **kwargs):
        pos = kwargs.get("position")
        if pos is not None:
            self._client.cover_set_position(self._ch, int(pos))
            self._position = int(pos)

    
    @property
    def current_cover_position(self):
        # Aus coordinator.data lesen (State‑Cache: {(raum, kanal): {...}})
        data = self.coordinator.data or {}
        key = (self._ch.raumindex, self._ch.kanalindex)
        st = data.get(key)
        if st and st.get("lastp") is not None:
            self._position = int(st["lastp"] // 2)  # 0..200 -> 0..100
        # Auslöser (optional, falls vorher gelesen)
        cause = self._client.cause_cache.get(self._ch.cli_index)
        if cause:
            self._last_cause = cause.get("cliausl")
        return self._position
    
    
    @property
    def is_closed(self):
        """Return if the cover is closed."""
        if self    if self._position is None:
            return None


    @property
    def extra_state_attributes(self):
        attrs = {}
        if self._last_cause is not None:
            attrs["last_cause_code"] = self._last_cause
        return attrs



async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    data = hass.data[DOMAIN]
    client = data["client"]
    coordinator = data["coordinator"]
    covers = data["mapped"]["cover"]
    entities = [WebControlCover(hass, client, coordinator, ch) for ch in covers]
    async_add_entities(entities)
