"""FileFlows integration for Home Assistant."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import FileFlowsApi, FileFlowsApiError, FileFlowsConnectionError
from .const import (
    ATTR_FILE_UID,
    ATTR_LIBRARY_UID,
    ATTR_NODE_UID,
    CONF_ACCESS_TOKEN,
    CONF_SSL,
    CONF_VERIFY_SSL,
    DEFAULT_PORT,
    DEFAULT_SSL,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
    SERVICE_DISABLE_NODE,
    SERVICE_ENABLE_NODE,
    SERVICE_PAUSE_SYSTEM,
    SERVICE_REPROCESS_FILE,
    SERVICE_RESCAN_LIBRARY,
    SERVICE_RESUME_SYSTEM,
)
from .coordinator import FileFlowsDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.SWITCH,
]

# Service schemas
SERVICE_NODE_SCHEMA = vol.Schema({
    vol.Required(ATTR_NODE_UID): cv.string,
})

SERVICE_LIBRARY_SCHEMA = vol.Schema({
    vol.Required(ATTR_LIBRARY_UID): cv.string,
})

SERVICE_FILE_SCHEMA = vol.Schema({
    vol.Required(ATTR_FILE_UID): cv.string,
})


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up FileFlows from a config entry."""
    host = entry.data[CONF_HOST]
    port = entry.data.get(CONF_PORT, DEFAULT_PORT)
    ssl = entry.data.get(CONF_SSL, DEFAULT_SSL)
    verify_ssl = entry.data.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL)
    access_token = entry.data.get(CONF_ACCESS_TOKEN)

    session = async_get_clientsession(hass, verify_ssl=verify_ssl)
    
    api = FileFlowsApi(
        host=host,
        port=port,
        ssl=ssl,
        verify_ssl=verify_ssl,
        access_token=access_token,
        session=session,
    )

    try:
        if not await api.test_connection():
            raise ConfigEntryNotReady(f"Unable to connect to FileFlows at {host}:{port}")
    except FileFlowsConnectionError as err:
        raise ConfigEntryNotReady(f"Connection error: {err}") from err

    coordinator = FileFlowsDataUpdateCoordinator(hass, api, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
        "coordinator": coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register services
    await _async_setup_services(hass, api)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
        
        # Remove services if no more entries
        if not hass.data[DOMAIN]:
            _async_remove_services(hass)
            
    return unload_ok


async def _async_setup_services(hass: HomeAssistant, api: FileFlowsApi) -> None:
    """Set up FileFlows services."""
    
    async def handle_pause_system(call: ServiceCall) -> None:
        """Handle pause system service call."""
        try:
            await api.pause_system()
            _LOGGER.info("FileFlows system paused")
        except FileFlowsApiError as err:
            _LOGGER.error("Failed to pause system: %s", err)

    async def handle_resume_system(call: ServiceCall) -> None:
        """Handle resume system service call."""
        try:
            await api.resume_system()
            _LOGGER.info("FileFlows system resumed")
        except FileFlowsApiError as err:
            _LOGGER.error("Failed to resume system: %s", err)

    async def handle_enable_node(call: ServiceCall) -> None:
        """Handle enable node service call."""
        node_uid = call.data[ATTR_NODE_UID]
        try:
            await api.enable_node(node_uid)
            _LOGGER.info("Node %s enabled", node_uid)
        except FileFlowsApiError as err:
            _LOGGER.error("Failed to enable node %s: %s", node_uid, err)

    async def handle_disable_node(call: ServiceCall) -> None:
        """Handle disable node service call."""
        node_uid = call.data[ATTR_NODE_UID]
        try:
            await api.disable_node(node_uid)
            _LOGGER.info("Node %s disabled", node_uid)
        except FileFlowsApiError as err:
            _LOGGER.error("Failed to disable node %s: %s", node_uid, err)

    async def handle_rescan_library(call: ServiceCall) -> None:
        """Handle rescan library service call."""
        library_uid = call.data[ATTR_LIBRARY_UID]
        try:
            await api.rescan_library(library_uid)
            _LOGGER.info("Library %s rescan started", library_uid)
        except FileFlowsApiError as err:
            _LOGGER.error("Failed to rescan library %s: %s", library_uid, err)

    async def handle_reprocess_file(call: ServiceCall) -> None:
        """Handle reprocess file service call."""
        file_uid = call.data[ATTR_FILE_UID]
        try:
            await api.reprocess_file(file_uid)
            _LOGGER.info("File %s reprocess started", file_uid)
        except FileFlowsApiError as err:
            _LOGGER.error("Failed to reprocess file %s: %s", file_uid, err)

    # Register services
    if not hass.services.has_service(DOMAIN, SERVICE_PAUSE_SYSTEM):
        hass.services.async_register(
            DOMAIN, SERVICE_PAUSE_SYSTEM, handle_pause_system
        )
    if not hass.services.has_service(DOMAIN, SERVICE_RESUME_SYSTEM):
        hass.services.async_register(
            DOMAIN, SERVICE_RESUME_SYSTEM, handle_resume_system
        )
    if not hass.services.has_service(DOMAIN, SERVICE_ENABLE_NODE):
        hass.services.async_register(
            DOMAIN, SERVICE_ENABLE_NODE, handle_enable_node, schema=SERVICE_NODE_SCHEMA
        )
    if not hass.services.has_service(DOMAIN, SERVICE_DISABLE_NODE):
        hass.services.async_register(
            DOMAIN, SERVICE_DISABLE_NODE, handle_disable_node, schema=SERVICE_NODE_SCHEMA
        )
    if not hass.services.has_service(DOMAIN, SERVICE_RESCAN_LIBRARY):
        hass.services.async_register(
            DOMAIN, SERVICE_RESCAN_LIBRARY, handle_rescan_library, schema=SERVICE_LIBRARY_SCHEMA
        )
    if not hass.services.has_service(DOMAIN, SERVICE_REPROCESS_FILE):
        hass.services.async_register(
            DOMAIN, SERVICE_REPROCESS_FILE, handle_reprocess_file, schema=SERVICE_FILE_SCHEMA
        )


def _async_remove_services(hass: HomeAssistant) -> None:
    """Remove FileFlows services."""
    hass.services.async_remove(DOMAIN, SERVICE_PAUSE_SYSTEM)
    hass.services.async_remove(DOMAIN, SERVICE_RESUME_SYSTEM)
    hass.services.async_remove(DOMAIN, SERVICE_ENABLE_NODE)
    hass.services.async_remove(DOMAIN, SERVICE_DISABLE_NODE)
    hass.services.async_remove(DOMAIN, SERVICE_RESCAN_LIBRARY)
    hass.services.async_remove(DOMAIN, SERVICE_REPROCESS_FILE)
