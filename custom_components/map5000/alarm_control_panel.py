
from homeassistant.components.alarm_control_panel import AlarmControlPanelEntity
from homeassistant.core import callback
from homeassistant.helpers.entity import DeviceInfo
from .const import DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    coord = data["coordinator"]
    client = data["client"]

    area_siid = entry.data.get("area_siid")
    if not area_siid:
        area_siid = await client.first_area_siid()
    async_add_entities([MapAlarmPanel(coord, client, area_siid)])

class MapAlarmPanel(AlarmControlPanelEntity):
    _attr_code_arm_required=False
    _attr_code_format=None

    def __init__(self, coord, client, area_siid: str):
        self._coord=coord; self._client=client; self._siid=area_siid
        self._state="disarmed"
        self._device_info = DeviceInfo(identifiers={(DOMAIN, "map5000")}, manufacturer="Bosch", model="MAP5000", name="MAP5000")
        coord.reg.async_add_listener(self._on_update)

    @property
    def device_info(self): return self._device_info
    @property
    def state(self): return self._state
    @property
    def name(self):  return "MAP5000 Alarm Panel"
    @property
    def unique_id(self): return f"{DOMAIN}_alarm_{self._siid}"

    @callback
    def _on_update(self, siid, payload):
        res=payload.get("resource", {})
        self_link=res.get("@self","")
        # incidents: /inc/<AreaSIID>/<id>
        if isinstance(self_link,str) and self_link.startswith("/inc/"):
            parts=self_link.split("/")
            if len(parts)>=3 and parts[2]==self._siid:
                if payload.get("etype")=="CREATED": self._state="triggered"
                elif payload.get("etype")=="DELETED": pass
                self.async_write_ha_state()
                return
        # area state
        if siid==self._siid or (isinstance(self_link,str) and self_link.endswith(self._siid)):
            armed = res.get("armed")
            if armed is True: self._state="armed_home"
            elif armed is False: self._state="disarmed"
            self.async_write_ha_state()

    async def async_alarm_disarm(self, code=None):
        await self._client.post(f"/{self._siid}", {"@cmd":"DISARM"})
    async def async_alarm_arm_home(self, code=None):
        await self._client.post(f"/{self._siid}", {"@cmd":"ARM"})
    async def async_alarm_arm_away(self, code=None):
        await self._client.post(f"/{self._siid}", {"@cmd":"ARM"})
