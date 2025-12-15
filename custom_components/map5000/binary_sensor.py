
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import callback
from homeassistant.helpers.entity import DeviceInfo
from .const import DOMAIN
from .coordinator import OIICoordinator, MapRegistry, DeviceEntry

async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    coord: OIICoordinator = data["coordinator"]
    reg: MapRegistry = data["registry"]

    entities=[]
    for siid, dev in reg.devices.items():
        if dev.type.startswith("POINT."):
            entities.append(MapBinarySensor(coord, reg, dev))
    async_add_entities(entities)

class MapBinarySensor(BinarySensorEntity):
    def __init__(self, coord: OIICoordinator, reg: MapRegistry, dev: DeviceEntry):
        self._coord=coord; self._reg=reg; self._dev=dev
        self._is_on=None; self._attrs={}
        self._attr_unique_id=f"{DOMAIN}_{dev.siid}"
        self._attr_name=dev.name or dev.siid
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
        mapping=self._reg.map_input(self._dev.type)
        val=self._reg.state_of(self._dev, res, mapping)
        if val is not None:
            self._is_on = bool(val)
            for k in ("armed","fault","name"):
                if k in res: self._attrs[k]=res[k]
            self.async_write_ha_state()
