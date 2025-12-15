
import httpx
from typing import Any, Dict, List, Optional

class OIIClient:
    def __init__(self, base_url: str, username: str, password: str, verify_tls: bool):
        self.base = base_url.rstrip("/")
        self.auth = httpx.DigestAuth(username, password)
        self.verify = verify_tls
        self._client: Optional[httpx.AsyncClient] = None
        self.subscription_url: Optional[str] = None

    async def open(self):
        self._client = httpx.AsyncClient(auth=self.auth, verify=self.verify, timeout=httpx.Timeout(30.0))

    async def close(self):
        if self._client:
            await self._client.aclose()

    async def get(self, path: str) -> Dict[str, Any]:
        r = await self._client.get(f"{self.base}{path}")
        r.raise_for_status()
        return r.json()

    async def post(self, path: str, body: Dict[str, Any], timeout: Optional[float] = None) -> Dict[str, Any]:
        r = await self._client.post(f"{self.base}{path}", json=body, timeout=timeout)
        if r.status_code in (200, 201):
            return r.json()
        if r.status_code == 202:
            return {}
        r.raise_for_status()
        return {}

    async def delete(self, path: str):
        r = await self._client.delete(f"{self.base}{path}")
        if r.status_code not in (200, 204):
            r.raise_for_status()

    async def load_device_config(self) -> List[Dict[str, Any]]:
        cfg = await self.get("/config")
        dc = cfg.get("deviceConfiguration")
        if isinstance(dc, list):
            return dc
        for _, v in cfg.items():
            if isinstance(v, dict) and isinstance(v.get("deviceConfiguration"), list):
                return v["deviceConfiguration"]
        return []

    async def first_area_siid(self) -> Optional[str]:
        cfg = await self.get("/config")
        areas = cfg.get("areaConfiguration") or []
        if isinstance(areas, list) and areas:
            return areas[0].get("siid")
        return None

    async def create_subscription(self, subs: List[Dict[str, Any]], buffer_size: int, lease_time: int) -> str:
        body = {"@cmd":"SUBSCRIBE","bufferSize":buffer_size,"leaseTime":lease_time,"subscriptions":subs}
        resp = await self.post("/sub", body)
        self.subscription_url = resp["subscriptionURL"]
        return self.subscription_url

    async def fetch_events(self, maxEvents: int, minEvents: int, maxTime: int) -> List[Dict[str, Any]]:
        assert self.subscription_url
        body = {"@cmd":"FETCHEVENTS","maxEvents":maxEvents,"minEvents":minEvents,"maxTime":maxTime}
        resp = await self.post(self.subscription_url, body, timeout=max(5.0, maxTime+10))
        return resp.get("evts", [])

    async def renew_subscription(self):
        if not self.subscription_url:
            return
        await self.post(self.subscription_url, {"@cmd":"FETCHEVENTS","maxEvents":0})
