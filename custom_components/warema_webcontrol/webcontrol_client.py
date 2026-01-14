from __future__ import annotations
import requests
import xml.etree.ElementTree as ET
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from threading import Lock

@dataclass
class ChannelInfo:
    cli_index: int
    name: str
    type: int
    lastp: Optional[int] = None
    lastw: Optional[int] = None
    maxw: Optional[int] = None
    minw: Optional[int] = None
    winakt: Optional[int] = None
    raumindex: Optional[int] = None
    kanalindex: Optional[int] = None


class WebControlClient:
    # Header & Limits
    BEFEHLSCODE = 0x90
    BEFEHLSZAEHLER_MAX = 254
    PAYLOADLENGTH_MAX = 46

    # TEL (Requests)
    TEL_RAUM_ABFRAGEN = 3
    TEL_KANALBEDIENUNG = 29
    TEL_POLLING = 39
    TEL_SPRACHE = 51
    TEL_CLIMATRONIC_KANAL_ABFRAGEN = 59
    TEL_CHECK_CLIMA_DATA = 61
    TEL_ABWESEND = 63
    TEL_SOMMER_WINTER_AKTIV = 71
    TEL_AUTOMATIK = 37
    TEL_AUSLOESER = 73

    # RES (ResponseIDs)
    RES_RAUM_ABFRAGEN = 4
    RES_KANALBEDIENUNG = 30
    RES_POLLING = 40
    RES_CLIMA_COM_BUSY = 41
    RES_SPRACHE = 52
    RES_CLIMATRONIC_KANAL_ABFRAGEN = 60
    RES_CHECK_CLIMA_DATA = 62
    RES_ABWESEND = 64
    RES_SOMMER_WINTER_AKTIV = 72
    RES_AUTOMATIK = 38
    RES_AUSLOESER = 74

    # Produkt-Typen (aus WebControl.js – für unsere Nutzung nur 2,3,4,5 & 12)
    TYPE_RAFFSTORE = 2
    TYPE_ROLLLADEN = 3
    TYPE_FALTSTORE = 4
    TYPE_JALOUSIE = 5

    TYPE_LICHT = 12
    TYPE_INVALID = 255

    # Funktionscodes
    FC_STOP = 1
    FC_STATE = 3
    FC_HOCH = 8
    FC_TIEF = 9

    INVALID_WINKEL = 32767
    DEF_MAXRAUM = 64
    DEF_MAXKANAL = 10

    def __init__(self, base_url: str, timeout: int = 5):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._counter = 0
        # init status
        self._lock = Lock()
        self._session = requests.Session()
        self.language: Optional[int] = None
        self.sommer_winter_aktiv: Optional[int] = None
        self.clima_check_erfolg: Optional[int] = None
        self.abwesend: Optional[bool] = None
        self.automatik: Optional[bool] = None
        # Ensure caches exist for coordinator
        self.state_cache: Dict[Tuple[int,int], Dict[str,int]] = {}
        self.cause_cache: Dict[int, Dict[str,int]] = {}

    # ---------- low-level helpers ----------
    @staticmethod
    def _to_hex(byte_array: List[int]) -> str:
        return ''.join(f'{b & 0xFF:02x}' for b in byte_array)

    def _next_counter(self) -> int:
        c = self._counter
        self._counter = 0 if c >= self.BEFEHLSZAEHLER_MAX else c + 1
        return c

    def _build_message(self, payload_bytes: List[int]) -> Tuple[str, int]:
        if not (1 <= len(payload_bytes) <= self.PAYLOADLENGTH_MAX):
            raise ValueError("Payload-Länge außerhalb des gültigen Bereichs")
        header_counter = self._next_counter()
        header = [self.BEFEHLSCODE, header_counter, len(payload_bytes)]
        full = header + payload_bytes
        return self._to_hex(full), header_counter

    def _parse_xml_response(self, xml_text: str) -> dict:
        """Parse Warema WebControl reponse XML: extract responseID + lastp (0..200)."""
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as e:
            return {"ok": False, "error": f"xml_parse_error: {e}"}

        def get_tag(*names: str) -> str | dict | None:
            for n in names:
                el = root.findall(n)
                if el is not None and el is dict:
                    ed = []
                    for e in el:
                        if e is not None and e.text is not None:
                            ed.append(e.text.strip())
                    return ed
                if el is not None and el.text is not None:
                    return el.text.strip()
            return None
        
        xml_tags = {"responseID", 
                    "befehlszaehler", 
                    "requestid", 
                    "feedback", 
                    "raumindex", 
                    "kanalindex", 
                    "lastp", 
                    "lastw", 
                    "raumname"
                    "clikanalindex",
                    "cliausl",
                    "erfolg",
                    "sprache",
                    "winterakt",
                    "maxw",
                    "minw",
                    "produkttyp",
                    "kanalname",
                    "winakt"}        
        
        result = {"ok": True}

        for xml_tag in xml_tags:
            tag = get_tag(xml_tag)
            if tag is not None:
                if xml_tag in {"kanalname", "raumname"}:
                    result.setdefault(xml_tag).append(tag)
                else:
                    if tag is dict:
                        for t in tag:
                            try:
                                result.setdefault(xml_tag, []).append(int(t))
                            except Exception:
                                result.setdefault(xml_tag, []).append(None)
                    else:
                        try:
                            result.setdefault(xml_tag).append(int(tag))
                        except Exception:
                            result.setdefault(xml_tag).append(None)
            else:
                result.setdefault(xml_tag).append(None)
        
        if result.get("responseID") is None:
            result["ok"] = False
            result["error"] = "missing or empty befehlszaehler"

        if result.get("befehlszaehler") is None:
            result["ok"] = False
            result["error"] = "missing or empty befehlszaehler"

        if result.get("responseID") == WebControlClient.RES_CLIMA_COM_BUSY:
            result["busy"] = True
        return result

    def _http_get(self, hex_string: str) -> str:
        url = f"{self.base_url}/protocol.xml"
        r = self._session.get(url, params={"protocol": hex_string}, timeout=self.timeout)
        r.raise_for_status()
        return self._parse_xml_response(r.text)

    def _send(self, payload: List[int], max_retries: int = 3, backoff_sec: float = 0.15) -> ET.Element:
        """Threadsafe sending + easy busy/counter validation
        returns the root element of the response XML
        """
        with self._lock:
            for attempt in range(max_retries):
                hex_msg, cnt = self._build_message(payload)
                response = self._http_get(hex_msg)

                # handle busy: responseID == RES_BUSY → kurz warten und erneut
                rid = response.get("responseID")

                # Counter validieren, wenn vorhanden
                cz = response.get("befehlszaehler")

                if rid == self.RES_CLIMA_COM_BUSY:
                    time.sleep(backoff_sec)
                    continue
                if cz is not None and cz != cnt:
                    # Gateway hat anderen Zähler gespiegelt → erneut senden
                    time.sleep(backoff_sec)
                    continue
                # OK
                return response
            # Alle Versuche durch: letztes Response zurückgeben (oder Fehler werfen)
            return response

    # ---------- single command helpers ----------
    def set_language_query(self) -> str:
        response = self._send([self.TEL_SPRACHE, 255])
        if response.get("ok") and response.get("responseID") == self.RES_SPRACHE:
            self.language = response.get("sprache")
        return response

    def query_clima_block(self, start_index: int) -> List[ChannelInfo]:
        response = self._send([self.TEL_CLIMATRONIC_KANAL_ABFRAGEN, start_index])
        if not response.get("ok") or response.get("responseID") == self.RES_CLIMATRONIC_KANAL_ABFRAGEN:
            return []
        names   = response.get("kanalname", [])
        types   = response.get("produkttyp", [])
        lastps  = response.get("lastp", [])
        lastws  = response.get("lastw", [])
        maxws   = response.get("maxw", [])
        minws   = response.get("minw", [])
        winakts = response.get("winakt", [])
        count = min(4, max(len(names), len(types), len(lastps), len(lastws)))
        channels: List[ChannelInfo] = []
        for i in range(count):
            idx = start_index + i
            channels.append(ChannelInfo(
                cli_index=idx,
                name= names[i]   if i < len(names)   else "",
                type= types[i]   if i < len(types)   else self.TYPE_INVALID,
                lastp=lastps[i]  if i < len(lastps)  else None,
                lastw=lastws[i]  if i < len(lastws)  else None,
                maxw= maxws[i]   if i < len(maxws)   else None,
                minw= minws[i]   if i < len(minws)   else None,
                winakt=winakts[i] if i < len(winakts) else None
            ))
        return channels

    def load_all_channels(self, max_elements: int = 144) -> List[ChannelInfo]:
        all_channels: List[ChannelInfo] = []
        for start in range(0, max_elements, 4):
            block = self.query_clima_block(start)
            if not block:
                break
            all_channels.extend(block)
        return all_channels

    def query_sommer_winter_aktiv(self) -> str:
        response = self._send([self.TEL_SOMMER_WINTER_AKTIV])
        if response.get("ok") and response.get("responseID") == self.RES_SOMMER_WINTER_AKTIV:
            winter = response.get("winterakt")
            self.sommer_winter_aktiv = winter if winter is not None else None
        return response

    def check_clima_data(self) -> str:
        response = self._send([self.TEL_CHECK_CLIMA_DATA])
        if response.get("ok") and response.get("responseID") == self.RES_CHECK_CLIMA_DATA:
            erfolg = response.get("erfolg")
            self.clima_check_erfolg = erfolg if erfolg is not None else None
        return response

    def load_rooms_matrix(self, max_rooms: int = DEF_MAXRAUM) -> Dict[int, Tuple[int,int]]:
        mapping: Dict[int, Tuple[int,int]] = {}
        for r in range(0, max_rooms):
            response = self._send([self.TEL_RAUM_ABFRAGEN, r])
            if not response.get("ok") and response.get("responseID") != self.RES_RAUM_ABFRAGEN:
                break
            raumname = response.get("raumname", "")
            if raumname is None or "":
                break
            clis = response.findall("clikanalindex") or
            for k, cli in enumerate(clis[:self.DEF_MAXKANAL]):
                if cli != 255:  # gültig
                    mapping[cli] = (r, k)
        return mapping

    def initialize(self, max_elements: int = 144) -> dict:
        self.set_language_query()
        channels = self.load_all_channels(max_elements)
        self.query_sommer_winter_aktiv()
        self.check_clima_data()
        cli_to_roomchan = self.load_rooms_matrix()
        valid = [ch for ch in channels if ch.type != self.TYPE_INVALID]
        for ch in valid:
            if ch.cli_index in cli_to_roomchan:
                ch.raumindex, ch.kanalindex = cli_to_roomchan[ch.cli_index]
        cover_types = { self.TYPE_RAFFSTORE, self.TYPE_ROLLLADEN, self.TYPE_FALTSTORE, self.TYPE_JALOUSIE }
        light_types = { self.TYPE_LICHT }
        mapped = {
            "cover":  [ch for ch in valid if ch.type in cover_types and ch.raumindex is not None],
            "light":  [ch for ch in valid if ch.type in light_types and ch.raumindex is not None],
        }
        return {
            "language": self.language,
            "sommer_winter_aktiv": self.sommer_winter_aktiv,
            "clima_check_erfolg": self.clima_check_erfolg,
            "channels_all": channels,
            "channels_valid": valid,
            "channels_mapped": mapped,
        }
    
    # ---------- Polling ----------
    def poll(self, raumindex: int, kanalindex: int) -> Optional[Dict[str,int]]:
        response = self._send([self.TEL_POLLING, raumindex, kanalindex, 0])
        if not response.get("ok") and response.get("responseID") != self.RES_POLLING:
            return None

        st = {
            "raumindex": response.get("raumindex"),
            "kanalindex": response.get("kanalindex"),
            "lastp": response.get("lastp"),
            "lastw": response.get("lastw")
        }
        self.state_cache[(raumindex, kanalindex)] = st
        return st

    # ---------- Auslöser ----------
    def read_ausloeser(self, raumindex: int, kanalindex: int, cli_index: int) -> Optional[Dict[str,int]]:
        response = self._send([self.TEL_AUSLOESER, raumindex, kanalindex, cli_index])
        if not response.get("ok") and response.get("responseID") != self.RES_AUSLOESER:
            return None
        
        data = {
            "raumindex": response.get("raumindex"),
            "kanalindex": response.get("kanalindex"),
            "clikanidx": response.get("clikanidx"),
            "cliausl": response.get("cliausl")
        }
        self.cause_cache[cli_index] = data
        return data
    
    # Bedienungen
    def _channel_command(self, raumindex: int, kanalindex: int, fc: int, pos: int, winkel: int) -> str:
        if winkel != self.INVALID_WINKEL and winkel < 0:
            winkel = (65535 + winkel + 1)
        hi = (winkel - (winkel % 256)) // 256
        lo = winkel % 256
        response = self._send([self.TEL_KANALBEDIENUNG, raumindex, kanalindex, fc, pos, hi, lo])
        return response

    def cover_set_position(self, ch: ChannelInfo, percent: int) -> str:
        if ch.raumindex is not None and ch.kanalindex is not None:
            self.read_ausloeser(ch.raumindex, ch.kanalindex, ch.cli_index)
        return self._channel_command(ch.raumindex, ch.kanalindex, self.FC_STATE, int(percent), self.INVALID_WINKEL)

    def cover_open(self, ch: ChannelInfo) -> str:
        if ch.raumindex is not None and ch.kanalindex is not None:
            self.read_ausloeser(ch.raumindex, ch.kanalindex, ch.cli_index)
        return self._channel_command(ch.raumindex, ch.kanalindex, self.FC_HOCH, 0, 0)

    def cover_close(self, ch: ChannelInfo) -> str:
        if ch.raumindex is not None and ch.kanalindex is not None:
            self.read_ausloeser(ch.raumindex, ch.kanalindex, ch.cli_index)
        return self._channel_command(ch.raumindex, ch.kanalindex, self.FC_TIEF, 0, 0)

    def cover_stop(self, ch: ChannelInfo) -> str:
        if ch.raumindex is not None and ch.kanalindex is not None:
            self.read_ausloeser(ch.raumindex, ch.kanalindex, ch.cli_index)
        return self._channel_command(ch.raumindex, ch.kanalindex, self.FC_STOP, 0, self.INVALID_WINKEL)

    def light_on(self, ch: ChannelInfo) -> str:
        return self._channel_command(ch.raumindex, ch.kanalindex, self.FC_STATE, 100, self.INVALID_WINKEL)

    def light_off(self, ch: ChannelInfo) -> str:
        return self._channel_command(ch.raumindex, ch.kanalindex, self.FC_STOP, 0, self.INVALID_WINKEL)

    # Switches (global): Abwesend & Automatik
    def set_abwesend(self, enabled: bool) -> Optional[bool]:
        # Annahme: TEL_ABWESEND mit Parameter 1/0
        response = self._send([self.TEL_ABWESEND, 1 if enabled else 0])
        if response.get("ok") and response.get("responseID") == self.RES_ABWESEND:
            self.abwesend = enabled
            return self.abwesend
        return None

    def set_automatik(self, enabled: bool) -> Optional[bool]:
        response = self._send([self.TEL_AUTOMATIK, 1 if enabled else 0])
        if response.get("ok") and response.get("responseID") == self.RES_AUTOMATIK:
            self.automatik = enabled
            return self.automatik
        return None
