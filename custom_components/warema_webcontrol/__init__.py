from __future__ import annotations
import logging
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers import discovery
from .webcontrol_client import WebControlClient

DOMAIN = "webcontrol"
_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["cover", "light", "switch", "binary_sensor", "sensor"]


def setup(hass: HomeAssistant, config: ConfigType) -> bool:
    conf = config.get(DOMAIN, {})
    base_url = conf.get("base_url", "http://192.168.99.198")

    client = WebControlClient(base_url=base_url, timeout=5)
    _LOGGER.info("WebControl Init: Sprache/Kanäle/SommerWinter/ClimaCheck")
    init = client.initialize(max_elements=144)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["client"] = client
    hass.data[DOMAIN]["mapped"] = init["channels_mapped"]

    for platform in PLATFORMS:
        discovery.load_platform(hass, platform, DOMAIN, {}, config)

    return True
