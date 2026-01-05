"""The FileFlows integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv

from .api import FileFlowsApi, FileFlowsApiError
from .const import (
    ATTR_FILE_UID,
    ATTR_FLOW_UID,
    ATTR_LIBRARY_UID,
    ATTR_NODE_UID,
    ATTR_TASK_UID,
    ATTR_WORKER_UID,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_SSL,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
    DEFAULT_PORT,
    DEFAULT_SSL,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
    SERVICE_ABORT_WORKER,
    SERVICE_DISABLE_FLOW,
    SERVICE_DISABLE_LIBRARY,
    SERVICE_DISABLE_NODE,
    SERVICE_ENABLE_FLOW,
    SERVICE_ENABLE_LIBRARY,
    SERVICE_ENABLE_NODE,
    SERVICE_FORCE_PROCESSING,
    SERVICE_PAUSE_SYSTEM,
    SERVICE_REPROCESS_FILE,
    SERVICE_RESCAN_ALL_LIBRARIES,
    SERVICE_RESCAN_LIBRARY,
    SERVICE_RESTART_SYSTEM,
    SERVICE_RESUME_SYSTEM,
    SERVICE_RUN_TASK,
    SERVICE_UNHOLD_FILES,
)
from .coordinator import FileFlowsDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SWITCH,
    Platform.BUTTON,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up FileFlows from a config entry."""
    api = FileFlowsApi(
        host=entry.data[CONF_HOST],
        port=entry.data.get(CONF_PORT, DEFAULT_PORT),
        ssl=entry.data.get(CONF_SSL, DEFAULT_SSL),
        verify_ssl=entry.data.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL),
        username=entry.data.get(CONF_USERNAME),
        password=entry.data.get(CONF_PASSWORD),
    )

    try:
        if not await api.test_connection():
            raise ConfigEntryNotReady("Cannot connect to FileFlows")
    except FileFlowsApiError as err:
        raise ConfigEntryNotReady(f"Error connecting to FileFlows: {err}") from err

    coordinator = FileFlowsDataUpdateCoordinator(hass, api)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register services
    await _async_register_services(hass)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        coordinator: FileFlowsDataUpdateCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.api.close()

    # Remove services if no more entries
    if not hass.data[DOMAIN]:
        for service in [
            SERVICE_PAUSE_SYSTEM,
            SERVICE_RESUME_SYSTEM,
            SERVICE_RESTART_SYSTEM,
            SERVICE_ENABLE_NODE,
            SERVICE_DISABLE_NODE,
            SERVICE_ENABLE_LIBRARY,
            SERVICE_DISABLE_LIBRARY,
            SERVICE_RESCAN_LIBRARY,
            SERVICE_RESCAN_ALL_LIBRARIES,
            SERVICE_ENABLE_FLOW,
            SERVICE_DISABLE_FLOW,
            SERVICE_REPROCESS_FILE,
            SERVICE_ABORT_WORKER,
            SERVICE_RUN_TASK,
            SERVICE_FORCE_PROCESSING,
            SERVICE_UNHOLD_FILES,
        ]:
            hass.services.async_remove(DOMAIN, service)

    return unload_ok


def _get_coordinator(hass: HomeAssistant) -> FileFlowsDataUpdateCoordinator:
    """Get the first coordinator."""
    for coordinator in hass.data[DOMAIN].values():
        return coordinator
    raise ValueError("No FileFlows coordinator found")


async def _async_register_services(hass: HomeAssistant) -> None:
    """Register FileFlows services."""

    # Skip if already registered
    if hass.services.has_service(DOMAIN, SERVICE_PAUSE_SYSTEM):
        return

    # =========================================================================
    # System Services
    # =========================================================================
    async def async_pause_system(call: ServiceCall) -> None:
        """Pause the system."""
        coordinator = _get_coordinator(hass)
        await coordinator.api.pause_system()
        await coordinator.async_request_refresh()

    async def async_resume_system(call: ServiceCall) -> None:
        """Resume the system."""
        coordinator = _get_coordinator(hass)
        await coordinator.api.resume_system()
        await coordinator.async_request_refresh()

    async def async_restart_system(call: ServiceCall) -> None:
        """Restart the system."""
        coordinator = _get_coordinator(hass)
        await coordinator.api.restart_system()

    # =========================================================================
    # Node Services
    # =========================================================================
    async def async_enable_node(call: ServiceCall) -> None:
        """Enable a node."""
        coordinator = _get_coordinator(hass)
        node_uid = call.data[ATTR_NODE_UID]
        await coordinator.api.enable_node(node_uid)
        await coordinator.async_request_refresh()

    async def async_disable_node(call: ServiceCall) -> None:
        """Disable a node."""
        coordinator = _get_coordinator(hass)
        node_uid = call.data[ATTR_NODE_UID]
        await coordinator.api.disable_node(node_uid)
        await coordinator.async_request_refresh()

    # =========================================================================
    # Library Services
    # =========================================================================
    async def async_enable_library(call: ServiceCall) -> None:
        """Enable a library."""
        coordinator = _get_coordinator(hass)
        lib_uid = call.data[ATTR_LIBRARY_UID]
        await coordinator.api.enable_library(lib_uid)
        await coordinator.async_request_refresh()

    async def async_disable_library(call: ServiceCall) -> None:
        """Disable a library."""
        coordinator = _get_coordinator(hass)
        lib_uid = call.data[ATTR_LIBRARY_UID]
        await coordinator.api.disable_library(lib_uid)
        await coordinator.async_request_refresh()

    async def async_rescan_library(call: ServiceCall) -> None:
        """Rescan a library."""
        coordinator = _get_coordinator(hass)
        lib_uid = call.data[ATTR_LIBRARY_UID]
        await coordinator.api.rescan_libraries([lib_uid])
        await coordinator.async_request_refresh()

    async def async_rescan_all_libraries(call: ServiceCall) -> None:
        """Rescan all enabled libraries."""
        coordinator = _get_coordinator(hass)
        await coordinator.api.rescan_all_libraries()
        await coordinator.async_request_refresh()

    # =========================================================================
    # Flow Services
    # =========================================================================
    async def async_enable_flow(call: ServiceCall) -> None:
        """Enable a flow."""
        coordinator = _get_coordinator(hass)
        flow_uid = call.data[ATTR_FLOW_UID]
        await coordinator.api.enable_flow(flow_uid)
        await coordinator.async_request_refresh()

    async def async_disable_flow(call: ServiceCall) -> None:
        """Disable a flow."""
        coordinator = _get_coordinator(hass)
        flow_uid = call.data[ATTR_FLOW_UID]
        await coordinator.api.disable_flow(flow_uid)
        await coordinator.async_request_refresh()

    # =========================================================================
    # File Services
    # =========================================================================
    async def async_reprocess_file(call: ServiceCall) -> None:
        """Reprocess a file."""
        coordinator = _get_coordinator(hass)
        file_uid = call.data[ATTR_FILE_UID]
        await coordinator.api.reprocess_file(file_uid)
        await coordinator.async_request_refresh()

    async def async_force_processing(call: ServiceCall) -> None:
        """Force processing of files."""
        coordinator = _get_coordinator(hass)
        file_uids = call.data.get(ATTR_FILE_UID, [])
        if isinstance(file_uids, str):
            file_uids = [file_uids]
        # This uses the force-processing endpoint
        await coordinator.api._post("/api/library-file/force-processing", file_uids)
        await coordinator.async_request_refresh()

    async def async_unhold_files(call: ServiceCall) -> None:
        """Unhold files."""
        coordinator = _get_coordinator(hass)
        file_uids = call.data.get(ATTR_FILE_UID, [])
        if isinstance(file_uids, str):
            file_uids = [file_uids]
        await coordinator.api.unhold_files(file_uids)
        await coordinator.async_request_refresh()

    # =========================================================================
    # Worker Services
    # =========================================================================
    async def async_abort_worker(call: ServiceCall) -> None:
        """Abort a worker."""
        coordinator = _get_coordinator(hass)
        worker_uid = call.data[ATTR_WORKER_UID]
        await coordinator.api.abort_worker(worker_uid)
        await coordinator.async_request_refresh()

    # =========================================================================
    # Task Services
    # =========================================================================
    async def async_run_task(call: ServiceCall) -> None:
        """Run a scheduled task."""
        coordinator = _get_coordinator(hass)
        task_uid = call.data[ATTR_TASK_UID]
        await coordinator.api.run_task(task_uid)

    # =========================================================================
    # Register all services
    # =========================================================================
    hass.services.async_register(
        DOMAIN,
        SERVICE_PAUSE_SYSTEM,
        async_pause_system,
        schema=vol.Schema({}),
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_RESUME_SYSTEM,
        async_resume_system,
        schema=vol.Schema({}),
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_RESTART_SYSTEM,
        async_restart_system,
        schema=vol.Schema({}),
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_ENABLE_NODE,
        async_enable_node,
        schema=vol.Schema({vol.Required(ATTR_NODE_UID): cv.string}),
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_DISABLE_NODE,
        async_disable_node,
        schema=vol.Schema({vol.Required(ATTR_NODE_UID): cv.string}),
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_ENABLE_LIBRARY,
        async_enable_library,
        schema=vol.Schema({vol.Required(ATTR_LIBRARY_UID): cv.string}),
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_DISABLE_LIBRARY,
        async_disable_library,
        schema=vol.Schema({vol.Required(ATTR_LIBRARY_UID): cv.string}),
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_RESCAN_LIBRARY,
        async_rescan_library,
        schema=vol.Schema({vol.Required(ATTR_LIBRARY_UID): cv.string}),
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_RESCAN_ALL_LIBRARIES,
        async_rescan_all_libraries,
        schema=vol.Schema({}),
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_ENABLE_FLOW,
        async_enable_flow,
        schema=vol.Schema({vol.Required(ATTR_FLOW_UID): cv.string}),
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_DISABLE_FLOW,
        async_disable_flow,
        schema=vol.Schema({vol.Required(ATTR_FLOW_UID): cv.string}),
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_REPROCESS_FILE,
        async_reprocess_file,
        schema=vol.Schema({vol.Required(ATTR_FILE_UID): cv.string}),
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_FORCE_PROCESSING,
        async_force_processing,
        schema=vol.Schema({vol.Required(ATTR_FILE_UID): vol.Any(cv.string, [cv.string])}),
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_UNHOLD_FILES,
        async_unhold_files,
        schema=vol.Schema({vol.Required(ATTR_FILE_UID): vol.Any(cv.string, [cv.string])}),
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_ABORT_WORKER,
        async_abort_worker,
        schema=vol.Schema({vol.Required(ATTR_WORKER_UID): cv.string}),
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_RUN_TASK,
        async_run_task,
        schema=vol.Schema({vol.Required(ATTR_TASK_UID): cv.string}),
    )
