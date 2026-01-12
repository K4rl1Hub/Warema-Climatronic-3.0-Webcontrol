
# custom_components/webcontrol/config_flow.py
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .const import (
    DOMAIN,
    CONF_BASE_URL,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
)
from .webcontrol_client import WebControlClient


class WebControlConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow für Warema WebControl."""
    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        errors = {}

        if user_input is not None:
            base_url = user_input[CONF_BASE_URL].rstrip("/")
            scan_interval = int(user_input[CONF_SCAN_INTERVAL])

            if scan_interval <= 0:
                errors["scan_interval"] = "invalid_scan_interval"
            else:
                client = WebControlClient(base_url)
                try:
                    # Verbindung testen (Sprache abfragen)
                    await self.hass.async_add_executor_job(client.set_language_query)
                except Exception:
                    errors["base_url"] = "cannot_connect"

                if not errors:
                    return self.async_create_entry(
                        title="Warema WebControl",
                        data={
                            CONF_BASE_URL: base_url,
                            CONF_SCAN_INTERVAL: scan_interval,
                        },
                    )

        schema = vol.Schema({
            vol.Required(CONF_BASE_URL,): str,
            vol.Required(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): int,
        })
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_import(self, import_config):
        """Optional: YAML‑Import unterstützen, falls vorhanden."""
        return await self.async_step_user(import_config)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """OptionsFlow für Intervall‑Änderungen."""
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None) -> FlowResult:
        if user_input is not None:
            scan_interval = int(user_input[CONF_SCAN_INTERVAL])
            if scan_interval <= 0:
                return self.async_show_form(
                    step_id="init",
                    data_schema=self._schema(),
                    errors={"scan_interval": "invalid_scan_interval"},
                )

            return self.async_create_entry(title="", data={
                CONF_SCAN_INTERVAL: scan_interval
            })

        return self.async_show_form(step_id="init", data_schema=self._schema())

    def _schema(self):
        current = self.config_entry.options.get(
            CONF_SCAN_INTERVAL,
            self.config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        )
        return vol.Schema({
            vol.Required(CONF_SCAN_INTERVAL, default=current): int
        })


def async_get_options_flow(config_entry):
    return OptionsFlowHandler(config_entry)
