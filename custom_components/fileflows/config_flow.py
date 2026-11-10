"""Config flow for FileFlows integration."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import (
    FileFlowsApi,
    FileFlowsApiDisabledError,
    FileFlowsApiError,
    FileFlowsAuthError,
)
from .const import (
    CONF_API_TOKEN,
    CONF_FENRUS_TOKEN,
    CONF_SCAN_INTERVAL,
    CONF_SSL,
    CONF_VERIFY_SSL,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SSL,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

TOKEN_SELECTOR = TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))
TOKENS = (CONF_API_TOKEN, CONF_FENRUS_TOKEN)

TOKEN_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_API_TOKEN): TOKEN_SELECTOR,
        vol.Optional(CONF_FENRUS_TOKEN): TOKEN_SELECTOR,
    }
)

USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Required(CONF_SSL, default=DEFAULT_SSL): bool,
        vol.Required(CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL): bool,
    }
).extend(TOKEN_SCHEMA.schema)


def _tokens(user_input: Mapping[str, Any]) -> dict[str, str | None]:
    """Return both token keys, None for blank ones, so stale tokens get cleared."""
    return {key: (user_input.get(key) or "").strip() or None for key in TOKENS}


def _connection(user_input: Mapping[str, Any]) -> dict[str, Any]:
    """Return the form input with a trimmed host and normalized tokens."""
    return {
        **user_input,
        CONF_HOST: user_input[CONF_HOST].strip(),
        **_tokens(user_input),
    }


async def _validate(hass: HomeAssistant, data: Mapping[str, Any]) -> dict[str, str]:
    """Return form errors for the given connection data."""
    try:
        api = FileFlowsApi(
            async_get_clientsession(
                hass, verify_ssl=data.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL)
            ),
            data[CONF_HOST],
            data.get(CONF_PORT, DEFAULT_PORT),
            data.get(CONF_SSL, DEFAULT_SSL),
            data.get(CONF_API_TOKEN),
            data.get(CONF_FENRUS_TOKEN),
        )
    except ValueError:
        # yarl rejects schemes, paths, spaces, empty hosts and bad ports
        return {CONF_HOST: "invalid_host"}
    if not data.get(CONF_API_TOKEN) and not data.get(CONF_FENRUS_TOKEN):
        return {"base": "no_token"}
    try:
        await api.async_validate()
    except FileFlowsAuthError:
        return {"base": "invalid_auth"}
    except FileFlowsApiDisabledError:
        return {"base": "api_disabled"}
    except FileFlowsApiError:
        return {"base": "cannot_connect"}
    except Exception:
        _LOGGER.exception("Unexpected exception")
        return {"base": "unknown"}
    return {}


class FileFlowsConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for FileFlows."""

    VERSION = 2

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            data = _connection(user_input)
            await self.async_set_unique_id(f"{data[CONF_HOST]}:{data[CONF_PORT]}")
            self._abort_if_unique_id_configured()
            if not (errors := await _validate(self.hass, data)):
                return self.async_create_entry(
                    title=f"FileFlows ({data[CONF_HOST]})", data=data
                )
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(USER_SCHEMA, user_input),
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Start reauthentication."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for new tokens."""
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()
        if user_input is not None:
            tokens = _tokens(user_input)
            if not (errors := await _validate(self.hass, {**entry.data, **tokens})):
                return self.async_update_reload_and_abort(entry, data_updates=tokens)
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=TOKEN_SCHEMA,
            errors=errors,
            description_placeholders={"host": entry.data[CONF_HOST]},
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Change connection settings."""
        errors: dict[str, str] = {}
        entry = self._get_reconfigure_entry()
        if user_input is not None:
            data = _connection(user_input)
            unique_id = f"{data[CONF_HOST]}:{data[CONF_PORT]}"
            if unique_id != entry.unique_id:
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()
            if not (errors := await _validate(self.hass, data)):
                return self.async_update_reload_and_abort(
                    entry,
                    unique_id=unique_id,
                    title=f"FileFlows ({data[CONF_HOST]})",
                    data_updates=data,
                )
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                USER_SCHEMA, user_input or entry.data
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> FileFlowsOptionsFlow:
        """Get the options flow for this handler."""
        return FileFlowsOptionsFlow()


class FileFlowsOptionsFlow(OptionsFlowWithReload):
    """Handle FileFlows options."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=self.config_entry.options.get(
                            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=10, max=3600)),
                }
            ),
        )
