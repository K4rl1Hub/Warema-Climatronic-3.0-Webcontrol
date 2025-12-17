from __future__ import annotations
import requests
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

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
    RES_POLLING = 30
    RES_SPRACHE = 52
    RES_CLIMATRONIC_KANAL_ABFRAGEN = 60
    RES_CHECK_CLIMA_DATA = 62
    RES_ABWESEND = 64
    RES_SOMMER_WINTER_AKTIV = 72
    RES_AUTOMATIK = 38
    RES_AUSLOESER = 74

    # Produkt-Typen (aus WebControl.js – für unsere Nutzung nur 3 & 12)
    TYPE_ROLLLADEN = 3
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
        self.language: Optional[int] = None
        self.sommer_winter_aktiv: Optional[int] = None
        self.clima_check_erfolg: Optional[int] = None
        self.abwesend: Optional[bool] = None
        self.automatik: Optional[bool] = None

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
        header = [self.BEFEHLSCODE, self._next_counter(), len(payload_bytes)]
        full = header + payload_bytes
        return self._to_hex(full), header[1]

    def _http_get(self, hex_string: str) -> str:
        url = f"{self.base_url}/protocol.xml"
        r = requests.get(url, params={"protocol": hex_string}, timeout=self.timeout)
        r.raise_for_status()
        return r.text

    # ---------- single command helpers ----------
    def set_language_query(self) -> str:
        payload = [self.TEL_SPRACHE, 255]
        hex_msg, _ = self._build_message(payload)
        xml = self._http_get(hex_msg)
        root = ET.fromstring(xml)
        rid_el = root.find("responseID")
        if rid_el is not None and int(rid_el.text) == self.RES_SPRACHE:
            el = root.find("sprache")
            self.language = int(el.text) if el is not None else None
        return xml

    def query_clima_block(self, start_index: int) -> List[ChannelInfo]:
        payload = [self.TEL_CLIMATRONIC_KANAL_ABFRAGEN, start_index]
        hex_msg, _ = self._build_message(payload)
        xml = self._http_get(hex_msg)
        root = ET.fromstring(xml)
        rid_el = root.find("responseID")
        if rid_el is None or int(rid_el.text) != self.RES_CLIMATRONIC_KANAL_ABFRAGEN:
            return []
        names   = [el.text.strip() if el is not None and el.text else "" for el in root.findall("kanalname")]
        types   = [int(el.text) for el in root.findall("produkttyp")]
        lastps  = [int(el.text) for el in root.findall("lastp")]
        lastws  = [int(el.text) for el in root.findall("lastw")]
        maxws   = [int(el.text) for el in root.findall("maxw")]
        minws   = [int(el.text) for el in root.findall("minw")]
        winakts = [int(el.text) for el in root.findall("winakt")]
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
        payload = [self.TEL_SOMMER_WINTER_AKTIV]
        hex_msg, _ = self._build_message(payload)
        xml = self._http_get(hex_msg)
        root = ET.fromstring(xml)
        rid_el = root.find("responseID")
        if rid_el is not None and int(rid_el.text) == self.RES_SOMMER_WINTER_AKTIV:
            winter_el = root.find("winterakt")
            self.sommer_winter_aktiv = int(winter_el.text) if winter_el is not None else None
        return xml

    def check_clima_data(self) -> str:
        payload = [self.TEL_CHECK_CLIMA_DATA]
        hex_msg, _ = self._build_message(payload)
        xml = self._http_get(hex_msg)
        root = ET.fromstring(xml)
        rid_el = root.find("responseID")
        if rid_el is not None and int(rid_el.text) == self.RES_CHECK_CLIMA_DATA:
            erfolg_el = root.find("erfolg")
            self.clima_check_erfolg = int(erfolg_el.text) if erfolg_el is not None else None
        return xml

    def load_rooms_matrix(self, max_rooms: int = DEF_MAXRAUM) -> Dict[int, Tuple[int,int]]:
        mapping: Dict[int, Tuple[int,int]] = {}
        for r in range(0, max_rooms):
            payload = [self.TEL_RAUM_ABFRAGEN, r]
            hex_msg, _ = self._build_message(payload)
            xml = self._http_get(hex_msg)
            root = ET.fromstring(xml)
            rid_el = root.find("responseID")
            if rid_el is None or int(rid_el.text) != self.RES_RAUM_ABFRAGEN:
                break
            raumname_el = root.find("raumname")
            raumname = (raumname_el.text or "").strip() if raumname_el is not None else ""
            if raumname == "":
                break
            clis = [int(el.text) for el in root.findall("clikanalindex")]
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
        cover_types = { self.TYPE_ROLLLADEN }
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

    # Bedienungen
    def _channel_command(self, raumindex: int, kanalindex: int, fc: int, pos: int, winkel: int) -> str:
        if winkel != self.INVALID_WINKEL and winkel < 0:
            winkel = (65535 + winkel + 1)
        hi = (winkel - (winkel % 256)) // 256
        lo = winkel % 256
        payload = [self.TEL_KANALBEDIENUNG, raumindex, kanalindex, fc, pos, hi, lo]
        hex_msg, _ = self._build_message(payload)
        return self._http_get(hex_msg)

    def cover_set_position(self, raumindex: int, kanalindex: int, percent: int) -> str:
        return self._channel_command(raumindex, kanalindex, self.FC_STATE, int(percent), self.INVALID_WINKEL)

    def cover_open(self, raumindex: int, kanalindex: int) -> str:
        return self._channel_command(raumindex, kanalindex, self.FC_HOCH, 0, 0)

    def cover_close(self, raumindex: int, kanalindex: int) -> str:
        return self._channel_command(raumindex, kanalindex, self.FC_TIEF, 0, 0)

    def cover_stop(self, raumindex: int, kanalindex: int) -> str:
        return self._channel_command(raumindex, kanalindex, self.FC_STOP, 0, self.INVALID_WINKEL)

    def light_on(self, raumindex: int, kanalindex: int) -> str:
        return self._channel_command(raumindex, kanalindex, self.FC_STATE, 100, self.INVALID_WINKEL)

    def light_off(self, raumindex: int, kanalindex: int) -> str:
        return self._channel_command(raumindex, kanalindex, self.FC_STOP, 0, self.INVALID_WINKEL)

    # Switches (global): Abwesend & Automatik
    def set_abwesend(self, enabled: bool) -> Optional[bool]:
        # Annahme: TEL_ABWESEND mit Parameter 1/0
        payload = [self.TEL_ABWESEND, 1 if enabled else 0]
        hex_msg, _ = self._build_message(payload)
        xml = self._http_get(hex_msg)
        root = ET.fromstring(xml)
        rid_el = root.find("responseID")
        if rid_el is not None and int(rid_el.text) == self.RES_ABWESEND:
            self.abwesend = enabled
            return self.abwesend
        return None

    def set_automatik(self, enabled: bool) -> Optional[bool]:
        payload = [self.TEL_AUTOMATIK, 1 if enabled else 0]
        hex_msg, _ = self._build_message(payload)
        xml = self._http_get(hex_msg)
        root = ET.fromstring(xml)
        rid_el = root.find("responseID")
        if rid_el is not None and int(rid_el.text) == self.RES_AUTOMATIK:
            self.automatik = enabled
            return self.automatik
        return None
