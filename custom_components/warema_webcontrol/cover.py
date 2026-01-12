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

    def __init__(self, hass: HomeAssistant, client, coordinator, ch):
        super().__init__(coordinator)
        self._client = client
        self._ch = ch
        self._attr_name = ch.name or f"Rollladen {ch.cli_index}"
        self._attr_unique_id = f"webcontrol_cover_{ch.cli_index}"
        self._attr_device_class = WAREMA_TO_HA_DEVICE_CLASS.get(ch.gerätetyp, "shutter")
        self._position = None
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, "webcontrol")}, name="Warema WebControl"
        )
        self._last_cause = None  # cliausl Code

        self._history = []
        self._last_triggered = None
        self._last_command = None
        self._command_source = None
        self._assumed_state = False



    async def async_open_cover(self, **kwargs):
        self._assumed_state = True # we assume it works, no API feedback
        self._push_history("open", self._determine_source())
        self.async_write_ha_state()
        await self._client.cover_open(self._ch)

    async def async_close_cover(self, **kwargs):
        self._assumed_state = True # we assume it works, no API feedback
        self._push_history("close", self._determine_source())
        self.async_write_ha_state()
        await self._client.cover_close(self._ch)

    async def async_stop_cover(self, **kwargs):
        self._assumed_state = True # we assume it works, no API feedback
        self._push_history("stop", self._determine_source())
        self.async_write_ha_state()
        await self._client.cover_stop(self._ch)

    async def asnyc_set_cover_position(self, **kwargs):
        pos = kwargs.get("position")
        self._assumed_state = True # we assume it works, no API feedback
        self._push_history("set_position", self._determine_source(), {"position": pos})
        self.async_write_ha_state()
        if pos is not None:
            await self._client.cover_set_position(self._ch, int(pos))
            self._position = int(pos)


    def _determine_source(self) -> str:
        # Minimalheuristik: Wenn ein User-Kontext existiert → "ui", sonst "service".
        # Bei Automationen setzt HA i. d. R. parent_id → hier vereinfachen wir bewusst.
        try:
            ctx = self.hass.context
            if ctx and getattr(ctx, "user_id", None):
                return "ui"
        except Exception:
            pass
        return "service"


    def _push_history(self, command: str, source: str, value: dict | None = None) -> None:
        entry = {
            "ts": dt_util.utcnow().isoformat(timespec="seconds"),
            "command": command,
            "source": source,
            "value": value or {},
        }
        hist = getattr(self, "_history", [])
        hist.append(entry)
        if len(hist) > self._history_max:
            hist.pop(0)
        self._history = hist
        self._last_triggered = entry["ts"]
        self._last_command = command
        self._command_source = source
    
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
        if self._position is None:
            return None


    @property
    def extra_state_attributes(self):
        attrs = {
            "last_triggered": getattr(self, "_last_triggered", None),
            "last_command": getattr(self, "_last_command", None),
            "command_source": getattr(self, "_command_source", None),
            "history": getattr(self, "_history", []),
            "assumed_state": getattr(self, "_assumed_state", False),
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
    data = await self._client.poll_state(self._room_index, self._ch.kanalindex)
    self._assumed_state = False # since we just polled the real state
    self._command_source = "poll_inferred"
    self.async_write_ha_state()
