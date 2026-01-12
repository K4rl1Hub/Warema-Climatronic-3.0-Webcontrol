
DOMAIN = "warema_webcontrol"
CONF_BASE_URL = "base_url"
CONF_SCAN_INTERVAL = "scan_interval"
DEFAULT_SCAN_INTERVAL = 30 # seconds

# Mapping Warema type to HA cover device_class 
WAREMA_TO_HA_DEVICE_CLASS: dict[str, str] = {
    "TYPE_RAFFSTORE": "blind",
    "TYPE_ROLLLADEN": "shutter",
    "TYPE_FALTSTORE": "curtain",
    "TYPE_JALOUSIE": "blind",
}
