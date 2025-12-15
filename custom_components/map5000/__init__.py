
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from .const import DOMAIN, PLATFORMS
from .api import OIIClient
from .coordinator import MapRegistry, OIICoordinator

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    data = dict(entry.data); opts = dict(entry.options)
    conf = {**data, **opts}
    client = OIIClient(
        base_url=conf["base_url"], username=conf["username"],
        password=conf["password"], verify_tls=conf.get("verify_tls", False)
    )
    await client.open()
    registry = MapRegistry(hass, conf)
    coordinator = OIICoordinator(hass, client, registry, conf)
    await coordinator.async_setup()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {"client": client, "registry": registry, "coordinator": coordinator, "conf": conf}
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    data = hass.data[DOMAIN].pop(entry.entry_id)
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    await data["coordinator"].async_shutdown()
    await data["client"].close()
    return unloaded
