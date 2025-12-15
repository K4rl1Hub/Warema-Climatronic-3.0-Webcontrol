
DOMAIN = "map5000"

# Config keys
CONF_BASE_URL = "base_url"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_VERIFY_TLS = "verify_tls"

CONF_INCLUDE_TYPES = "include_types"
CONF_EXCLUDE_TYPES = "exclude_types"
CONF_INCLUDE_SIIDS = "include_siids"
CONF_EXCLUDE_SIIDS = "exclude_siids"

CONF_TYPE_MAPPING   = "type_mapping"    # inputs
CONF_OUTPUT_MAPPING = "output_mapping"  # outputs

# Subscription tunables
CONF_SUB_BUFFER = "sub_buffer"
CONF_SUB_LEASE  = "sub_lease"
CONF_FETCH_MAXEVENTS = "fetch_max_events"
CONF_FETCH_MINEVENTS = "fetch_min_events"
CONF_FETCH_MAXTIME   = "fetch_max_time"

DEFAULT_BUFFER = 200
DEFAULT_LEASE  = 300
DEFAULT_FETCH_MAXEVENTS = 50
DEFAULT_FETCH_MINEVENTS = 1
DEFAULT_FETCH_MAXTIME   = 60

PLATFORMS = ["binary_sensor", "switch", "alarm_control_panel"]
