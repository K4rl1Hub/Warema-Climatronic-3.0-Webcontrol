
from __future__ import annotations
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from .const import *

DEFAULT_INPUT_MAPPING = {
  "POINT.LSNEXPANDER":{"device_class":"opening","state_property":"open","true_values":[True,"OPEN","ON",1],"false_values":[False,"CLOSED","OFF",0]},
  "POINT.PIR":{"device_class":"motion","state_property":"active","true_values":[True,"ALARM","ON",1],"false_values":[False,"IDLE","OFF",0]},
  "POINT.TAMPER":{"device_class":"tamper","state_property":"alarm","true_values":[True,"ALARM","TAMPER","OPEN"],"false_values":[False,"NORMAL","CLOSED"]},
  "default":{"device_class":"problem","state_property":"state","true_values":["ALARM","ON",True],"false_values":["NORMAL","OFF",False]}
}
DEFAULT_OUTPUT_MAPPING = {
  "OUTPUT.SIREN":{"platform":"switch","state_property":"on","true_values":[True],"false_values":[False],"turn_on":{"@cmd":"ON"},"turn_off":{"@cmd":"OFF"}},
  "OUTPUT.STROBE":{"platform":"switch","state_property":"on","true_values":[True],"false_values":[False],"turn_on":{"@cmd":"ON"},"turn_off":{"@cmd":"OFF"}},
  "OUTPUT.LED":{"platform":"switch","state_property":"on","true_values":[True],"false_values":[False],"turn_on":{"@cmd":"ON"},"turn_off":{"@cmd":"OFF"}},
  "OUTPUT.KPSPEAKER":{"platform":"switch","state_property":"on","true_values":[True],"false_values":[False],"turn_on":{"@cmd":"ON"},"turn_off":{"@cmd":"OFF"}}
}

class Map5000ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION=1
    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="MAP5000 OII", data=user_input)
        schema = vol.Schema({
          vol.Required(CONF_BASE_URL): str,
          vol.Required(CONF_USERNAME): str,
          vol.Required(CONF_PASSWORD): str,
          vol.Optional(CONF_VERIFY_TLS, default=False): bool,
          vol.Optional(CONF_SUB_BUFFER, default=DEFAULT_BUFFER): int,
          vol.Optional(CONF_SUB_LEASE,  default=DEFAULT_LEASE): int,
          vol.Optional(CONF_FETCH_MAXEVENTS, default=DEFAULT_FETCH_MAXEVENTS): int,
          vol.Optional(CONF_FETCH_MINEVENTS, default=DEFAULT_FETCH_MINEVENTS): int,
          vol.Optional(CONF_FETCH_MAXTIME, default=DEFAULT_FETCH_MAXTIME): int,
        })
        return self.async_show_form(step_id="user", data_schema=schema)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return OptionsFlow(config_entry)

class OptionsFlow(config_entries.OptionsFlow):
    def __init__(self, entry): self.entry=entry

    async def async_step_init(self, user_input=None):
        opts=self.entry.options.copy()
        if user_input is not None:
            opts.update(user_input)
            return self.async_create_entry(title="MAP5000 Options", data=opts)
        schema = vol.Schema({
          vol.Optional(CONF_INCLUDE_TYPES, default=opts.get(CONF_INCLUDE_TYPES, ["POINT.LSNEXPANDER","POINT.PIR","POINT.TAMPER","OUTPUT."])): [str],
          vol.Optional(CONF_EXCLUDE_TYPES, default=opts.get(CONF_EXCLUDE_TYPES, ["SYSTEM.","SUPERV.","OII"])): [str],
          vol.Optional(CONF_TYPE_MAPPING,   default=opts.get(CONF_TYPE_MAPPING, DEFAULT_INPUT_MAPPING)): dict,
          vol.Optional(CONF_OUTPUT_MAPPING, default=opts.get(CONF_OUTPUT_MAPPING, DEFAULT_OUTPUT_MAPPING)): dict,
        })
        return self.async_show_form(step_id="init", data_schema=schema)
