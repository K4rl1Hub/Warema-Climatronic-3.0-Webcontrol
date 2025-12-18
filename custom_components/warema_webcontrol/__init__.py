from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .webcontrol_client import WebControlClient, ChannelInfo
from .const import DOMAIN, CONF_BASE_URL, CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["cover", "light", "switch", "binary_sensor", "sensor"]



async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Setup per UI Flow erstellt."""
    base_url = entry.data[CONF_BASE_URL]
    scan_seconds = entry.options.get(CONF_SCAN_INTERVAL, entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))

    client = WebControlClient(base_url=base_url, timeout=5)


    # Initialisierung im Threadpool (blockiert sonst)
    init = await hass.async_add_executor_job(client.initialize, 144)

    mapped = init["channels_mapped"]
    covers: list[ChannelInfo] = mapped.get("cover", [])
    lights: list[ChannelInfo] = mapped.get("light", [])

    async def _async_update():
        try:
            # Polling im Threadpool (alle relevanten Channels)
            def _do_poll():
                for ch in covers + lights:
                    if ch.raumindex is not None and ch.kanalindex is not None:
                        client.poll(ch.raumindex, ch.kanalindex)
                return client.state_cache
            return await hass.async_add_executor_job(_do_poll)
        except Exception as exc:
            raise UpdateFailed(str(exc)) from exc

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="webcontrol_coordinator",
        update_method=_async_update,
        update_interval=timedelta(seconds=int(scan_seconds)),
    )

    # Erste Aktualisierung
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["client"] = client
    hass.data[DOMAIN]["mapped"] = mapped
    hass.data[DOMAIN]["coordinator"] = coordinator

    # Plattformen laden
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data.pop(DOMAIN, None)
    return unload_ok
