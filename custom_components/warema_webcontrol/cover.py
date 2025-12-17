from __future__ import annotations
from homeassistant.components.cover import CoverEntity, CoverEntityFeature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from . import DOMAIN

class WebControlCover(CoverEntity):
    _attr_supported_features = (
        CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE |
        CoverEntityFeature.STOP | CoverEntityFeature.SET_POSITION
    )

    def __init__(self, client, ch):
        self._client = client
        self._ch = ch
        self._attr_name = ch.name or f"Rollladen {ch.cli_index}"
        self._attr_unique_id = f"webcontrol_cover_{ch.cli_index}"
        self._position = None
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, "webcontrol")}, name="Warema WebControl"
        )

    def open_cover(self, **kwargs):
        self._client.cover_open(self._ch.raumindex, self._ch.kanalindex)

    def close_cover(self, **kwargs):
        self._client.cover_close(self._ch.raumindex, self._ch.kanalindex)

    def stop_cover(self, **kwargs):
        self._client.cover_stop(self._ch.raumindex, self._ch.kanalindex)

    def set_cover_position(self, **kwargs):
        pos = kwargs.get("position")
        if pos is not None:
            self._client.cover_set_position(self._ch.raumindex, self._ch.kanalindex, int(pos))
            self._position = int(pos)

    @property
    def current_cover_position(self):
        return self._position


def setup_platform(hass: HomeAssistant, config, add_entities, discovery_info=None):
    data = hass.data[DOMAIN]
    client = data["client"]
    covers = data["mapped"]["cover"]
    entities = [WebControlCover(client, ch) for ch in covers]
    add_entities(entities, True)
