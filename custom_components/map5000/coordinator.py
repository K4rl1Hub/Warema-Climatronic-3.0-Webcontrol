
import asyncio, logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Callable
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from .api import OIIClient
from .const import *

_LOGGER = logging.getLogger(__name__)

@dataclass
class DeviceEntry:
    siid: str
    type: str
    name: Optional[str]
    raw: Dict[str, Any]

class MapRegistry:
    def __init__(self, hass: HomeAssistant, conf: Dict[str, Any]):
        self.hass = hass
        self.conf = conf
        self.devices: Dict[str, DeviceEntry] = {}
        self.listeners: List[Callable[[str, Dict[str, Any]], None]] = []
        self._last_resource: Dict[str, Dict[str, Any]] = {} # Cache

    def _matches(self, val: str, patterns: List[str]) -> bool:
        for p in patterns or []:
            if p.endswith("."):
                if val.startswith(p): return True
            elif p == val: return True
        return False

    def should_publish(self, entry: DeviceEntry) -> bool:
        inc_t = self.conf.get(CONF_INCLUDE_TYPES) or []
        exc_t = self.conf.get(CONF_EXCLUDE_TYPES) or []
        inc_s = set(self.conf.get(CONF_INCLUDE_SIIDS) or [])
        exc_s = set(self.conf.get(CONF_EXCLUDE_SIIDS) or [])
        if entry.siid in exc_s: return False
        if self._matches(entry.type, exc_t): return False
        if inc_s and entry.siid not in inc_s: return False
        if inc_t and not self._matches(entry.type, inc_t): return False
        return True

    def add_from_config(self, device_cfg: List[Dict[str, Any]]):
        cnt = 0
        for d in device_cfg:
            if not isinstance(d, dict): continue
            siid = d.get("siid"); dtype = d.get("type"); name = d.get("name")
            if not siid or not dtype: continue
            e = DeviceEntry(siid=siid, type=dtype, name=name, raw=d)
            if self.should_publish(e):
                self.devices[siid] = e; cnt += 1
        _LOGGER.info("Geräte registriert: %s", cnt)

    def map_input(self, dtype: str) -> Dict[str, Any]:
        tm = self.conf.get(CONF_TYPE_MAPPING) or {}
        return tm.get(dtype, tm.get("default", {"device_class":"opening","state_property":"state",
                                                "true_values":[True, "OPEN", "ON", 1],
                                                "false_values":[False, "CLOSED", "OFF", 0]}))

    def map_output(self, dtype: str) -> Dict[str, Any]:
        om = self.conf.get(CONF_OUTPUT_MAPPING) or {}
        if dtype in om:
            return om[dtype]
        for key, val in om.items():
            if key.endswith(".") and dtype.startswith(key):
                return val
        return {"platform":"switch","state_property":"on","true_values":[True],"false_values":[False],
                "turn_on":{"@cmd":"ON"},"turn_off":{"@cmd":"OFF"}}

    def state_of(self, entry: DeviceEntry, resource: Dict[str, Any], mapping: Dict[str, Any]) -> Optional[bool]:
        prop = mapping.get("state_property")
        tvals = set(map(str, mapping.get("true_values", [True])))
        fvals = set(map(str, mapping.get("false_values", [False])))
        v = None
        if prop and prop in resource:
            v = resource.get(prop)
        else:
            for k in ("on","active","open","alarm","state","value"):
                if k in resource:
                    v = resource[k]; break
        if v is None:
            return None
        if isinstance(v, bool):
            return v
        if str(v) in tvals: return True
        if str(v) in fvals: return False
        return None

    @callback
    def async_add_listener(self, cb: Callable[[str, Dict[str, Any]], None]):
        self.listeners.append(cb)

    def dispatch(self, siid: str, payload: Dict[str, Any]):
        # Last know resource snapshot (cache) for initial state
        res = payload.get("resource")
        if isinstance(res, dict):
            self._last_resource[siid] = res
        for cb in list(self.listeners):
            try: cb(siid, payload)
            except Exception: _LOGGER.exception("Listener error")

    def get_last_resource(self, siid: str) -> Optional[Dict[str, Any]]:
        """Return last know resource snapshot for entity (if available)."""
        return self._last_resource.get(siid)

class OIICoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, client: OIIClient, reg: MapRegistry, conf: Dict[str, Any]):
        super().__init__(hass, _LOGGER, name="MAP5000 OII", update_interval=None)
        self.client=client; self.reg=reg; self.conf=conf
        self._poll_task: Optional[asyncio.Task] = None
        self._lease_expire: float = 0.0

    async def async_setup(self):
        device_cfg = await self.client.load_device_config()
        self.reg.add_from_config(device_cfg)

        # Initial snapshot
        for siid, dev in list(self.reg.devices.items()):
            try:
                res = await self.client.get(f"/{siid}")
                self.reg.dispatch(siid, {"resource": res})
            except Exception: pass

        subs = [{"eventType":["CHANGED","CREATED","DELETED"], "urls":["/devices","/points","/areas","/inc/*"]}]
        await self.client.create_subscription(subs, self.conf.get(CONF_SUB_BUFFER, DEFAULT_BUFFER),
                                             self.conf.get(CONF_SUB_LEASE, DEFAULT_LEASE))
        self._poll_task = self.hass.async_create_task(self._loop())

    async def _loop(self):
        lease = self.conf.get(CONF_SUB_LEASE, DEFAULT_LEASE)
        self._lease_expire = self.hass.loop.time() + max(10, lease-30)
        while True:
            try:
                evts = await self.client.fetch_events(self.conf.get(CONF_FETCH_MAXEVENTS, DEFAULT_FETCH_MAXEVENTS),
                                                      self.conf.get(CONF_FETCH_MINEVENTS, DEFAULT_FETCH_MINEVENTS),
                                                      self.conf.get(CONF_FETCH_MAXTIME, DEFAULT_FETCH_MAXTIME))
                for e in evts:
                    res = e.get("evt", {})
                    self_link = res.get("@self")
                    siid = res.get("siid")
                    if not siid and isinstance(self_link, str) and self_link.startswith("/"):
                        siid = self_link.split("/")[-1]
                    if siid:
                        self.reg.dispatch(siid, {"resource": res, "etype": e.get("type")})

                now = self.hass.loop.time()
                if now >= self._lease_expire:
                    await self.client.renew_subscription()
                    self._lease_expire = now + max(10, lease-30)
            except asyncio.CancelledError:
                break
            except Exception as ex:
                _LOGGER.error("Event loop error: %s", ex)
                await asyncio.sleep(5)

    async def async_shutdown(self):
        if self._poll_task:
            self._poll_task.cancel()
            try: await self._poll_task
            except Exception: pass
