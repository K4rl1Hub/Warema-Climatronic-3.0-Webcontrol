from __future__ import annotations
from homeassistant.components.cover import CoverEntity, CoverEntityFeature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util
from .const import WAREMA_TO_HA_DEVICE_CLASS

from . import DOMAIN

class WebControlCover(CoordinatorEntity, CoverEntity):
    _attr_supported_features = (
        CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE |
        CoverEntityFeature.STOP | CoverEntityFeature.SET_POSITION
    )
    _attr_should_poll = False
    _history_max = 20  # max number of history entries to keep

    def __init__(self, hass: HomeAssistant, client, coordinator, ch):
        super().__init__(coordinator)
        self._client = client
        self._ch = ch
        self._attr_name = ch.name or f"Rollladen {ch.cli_index}"
        self._attr_unique_id = f"webcontrol_cover_{ch.cli_index}"
        self._attr_device_class = WAREMA_TO_HA_DEVICE_CLASS.get(ch.type, "shutter")
        self._position = None
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, "webcontrol")}, name="Warema WebControl"
        )
        self._last_cause = None  # cliausl Code

        self._last_triggered = None
        self._last_command = None
        self._last_direction = None



    def open_cover(self, **kwargs):
        self._direction = "opening"
        self._is_moving = True
        self._last_command = "open"
        self._push_history(self._direction)
        self.schedule_update_ha_state()
        self._client.cover_open(self._ch)

    def close_cover(self, **kwargs):
        self._direction = "closing"
        self._is_moving = True
        self._last_command = "close"
        self._push_history()
        self.schedule_update_ha_state()
        self._client.cover_close(self._ch)

    def stop_cover(self, **kwargs):
        self._direction = "closing"
        self._is_moving = False
        self._last_command = "stop"
        self._push_history()
        self.schedule_update_ha_state()
        self._client.cover_stop(self._ch)

    def set_cover_position(self, **kwargs):
        pos = kwargs.get("position")
        self._direction = "closing" if pos > self._position else "opening"
        self._is_moving = True
        self._last_command = f"set_position {pos}"
        self._push_history()
        self.schedule_update_ha_state()
        if pos is not None:
            self._client.cover_set_position(self._ch, int(pos))
            self._position = int(pos)


    def _push_history(self) -> None:
        self._last_direction = self._direction
        self._last_triggered = dt_util.utcnow().isoformat(timespec="seconds")

    
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
    def is_closing(self) -> bool | None:
        return bool(getattr(self, "_is_moving", False)) and getattr(self, "_direction", None) == "closing"
    
    @property
    def is_opening(self) -> bool | None:
        return bool(getattr(self, "_is_moving", False)) and getattr(self, "_direction", None) == "opening"
    
    @property
    def is_closed(self) -> bool | None:
        """Return if the cover is closed."""
        pos = getattr(self, "_position", None)
        return None if pos is None else pos == 0
        


    @property
    def extra_state_attributes(self):
        attrs = {
            "last_triggered": getattr(self, "_last_triggered", None),
            "last_command": getattr(self, "_last_command", None),
            "last_direction": getattr(self, "_last_direction", None),
        }
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

async def async_update(self):
    data = self._client.poll_state(self._room_index, self._ch.kanalindex)
    if data:
        pos = data.get("lastp")
        if pos is not None:
            self._position = int(pos // 2)
        cause = self._client.cause_cache.get(self._ch.cli_index)
        if cause:
            self._last_cause = cause.get("cliausl")
    self.async_write_ha_state()
