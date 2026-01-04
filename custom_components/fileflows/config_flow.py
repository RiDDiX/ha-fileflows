"""Config flow for FileFlows integration."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import FileFlowsApi, FileFlowsApiError, FileFlowsAuthError, FileFlowsConnectionError
from .const import (
    CONF_ACCESS_TOKEN,
    CONF_SSL,
    CONF_VERIFY_SSL,
    DEFAULT_PORT,
    DEFAULT_SSL,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


def get_schema(
    host: str = "",
    port: int = DEFAULT_PORT,
    ssl: bool = DEFAULT_SSL,
    verify_ssl: bool = DEFAULT_VERIFY_SSL,
    access_token: str = "",
) -> vol.Schema:
    """Get the config schema."""
    return vol.Schema(
        {
            vol.Required(CONF_HOST, default=host): str,
            vol.Required(CONF_PORT, default=port): int,
            vol.Required(CONF_SSL, default=ssl): bool,
            vol.Required(CONF_VERIFY_SSL, default=verify_ssl): bool,
            vol.Optional(CONF_ACCESS_TOKEN, default=access_token): str,
        }
    )


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    session = async_get_clientsession(hass, verify_ssl=data.get(CONF_VERIFY_SSL, True))
    
    api = FileFlowsApi(
        host=data[CONF_HOST],
        port=data.get(CONF_PORT, DEFAULT_PORT),
        ssl=data.get(CONF_SSL, DEFAULT_SSL),
        verify_ssl=data.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL),
        access_token=data.get(CONF_ACCESS_TOKEN),
        session=session,
    )

    try:
        # Test connection with status endpoint
        if not await api.test_connection():
            raise CannotConnect("Connection test failed")
        # Get version info
        version = await api.get_version()
    except FileFlowsAuthError as err:
        raise InvalidAuth from err
    except FileFlowsConnectionError as err:
        raise CannotConnect from err
    except FileFlowsApiError as err:
        raise CannotConnect from err

    return {"title": f"FileFlows ({data[CONF_HOST]})", "version": version}


class FileFlowsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for FileFlows."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                # Check if already configured
                await self.async_set_unique_id(
                    f"{user_input[CONF_HOST]}:{user_input.get(CONF_PORT, DEFAULT_PORT)}"
                )
                self._abort_if_unique_id_configured()

                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=get_schema(),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> FileFlowsOptionsFlowHandler:
        """Get the options flow for this handler."""
        return FileFlowsOptionsFlowHandler(config_entry)


class FileFlowsOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle FileFlows options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        "scan_interval",
                        default=self.config_entry.options.get("scan_interval", 30),
                    ): vol.All(vol.Coerce(int), vol.Range(min=10, max=300)),
                }
            ),
        )


class CannotConnect(Exception):
    """Error to indicate we cannot connect."""


class InvalidAuth(Exception):
    """Error to indicate there is invalid auth."""
