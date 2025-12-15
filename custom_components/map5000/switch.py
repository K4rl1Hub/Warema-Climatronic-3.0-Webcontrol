
from homeassistant.components.switch import SwitchEntity
from homeassistant.core import callback
from homeassistant.helpers.entity import DeviceInfo
from .const import DOMAIN
from .coordinator import OIICoordinator, MapRegistry, DeviceEntry

async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    coord: OIICoordinator = data["coordinator"]
    reg: MapRegistry = data["registry"]
    client = data["client"]

    ents=[]
    for siid, dev in reg.devices.items():
        if dev.type.startswith("OUTPUT."):
            ents.append(MapOutputSwitch(coord, reg, client, dev))
    async_add_entities(ents)

class MapOutputSwitch(SwitchEntity):
    def __init__(self, coord: OIICoordinator, reg: MapRegistry, client, dev: DeviceEntry):
        self._coord=coord; self._reg=reg; self._client=client; self._dev=dev
        self._is_on=None
        self._attrs={}
        self._mapping = reg.map_output(dev.type)
        self._attr_unique_id=f"{DOMAIN}_out_{dev.siid}"
        self._attr_name=dev.name or dev.siid
        self._attr_available=True
        self._device_info = DeviceInfo(identifiers={(DOMAIN, "map5000")}, manufacturer="Bosch", model="MAP5000", name="MAP5000")

        reg.async_add_listener(self._on_update)

    @property
    def device_info(self): return self._device_info
    @property
    def is_on(self): return self._is_on
    @property
    def extra_state_attributes(self): return self._attrs

    @callback
    def _on_update(self, siid, payload):
        if siid!=self._dev.siid: return
        res=payload.get("resource", {})
        # availability
        self._attr_available = (res.get("opState") == "OK") and bool(res.get("enabled", True))
        val=self._reg.state_of(self._dev, res, self._mapping)
        if val is not None:
            self._is_on = bool(val)
        for k in ("opState","enabled","incs","name"):
            if k in res: self._attrs[k]=res[k]
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs):
        body = self._mapping.get("turn_on", {"@cmd":"ON"})
        await self._client.post(f"/{self._dev.siid}", body)
        try:
            res = await self._client.get(f"/{self._dev.siid}")
            self._on_update(self._dev.siid, {"resource": res})
        except Exception:
            pass

    async def async_turn_off(self, **kwargs):
        body = self._mapping.get("turn_off", {"@cmd":"OFF"})
        await self._client.post(f"/{self._dev.siid}", body)
        try:
            res = await self._client.get(f"/{self._dev.siid}")
            self._on_update(self._dev.siid, {"resource": res})
        except Exception:
            pass
