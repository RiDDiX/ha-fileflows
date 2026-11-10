"""The FileFlows integration."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import ATTR_CONFIG_ENTRY_ID, CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryAuthFailed, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType

from .api import FileFlowsApi
from .const import (
    ATTR_FILE_UID,
    ATTR_FLOW_UID,
    ATTR_LIBRARY_UID,
    ATTR_MINUTES,
    ATTR_NODE_UID,
    ATTR_TASK_UID,
    ATTR_WORKER_UID,
    CONF_API_TOKEN,
    CONF_FENRUS_TOKEN,
    CONF_SSL,
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
from .coordinator import FileFlowsConfigEntry, FileFlowsDataUpdateCoordinator

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SWITCH,
    Platform.BUTTON,
]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

UID_LIST = vol.All(cv.ensure_list, vol.Length(min=1), [cv.string])

ServiceFn = Callable[[FileFlowsApi, dict[str, Any]], Awaitable[None]]

SERVICES: dict[str, tuple[dict[Any, Any], ServiceFn]] = {
    SERVICE_PAUSE_SYSTEM: (
        {
            vol.Optional(ATTR_MINUTES): vol.All(
                vol.Coerce(int), vol.Range(min=1, max=525600)
            )
        },
        lambda api, d: api.pause_system(d.get(ATTR_MINUTES)),
    ),
    SERVICE_RESUME_SYSTEM: ({}, lambda api, d: api.resume_system()),
    SERVICE_RESTART_SYSTEM: ({}, lambda api, d: api.restart_system()),
    SERVICE_ENABLE_NODE: (
        {vol.Required(ATTR_NODE_UID): cv.string},
        lambda api, d: api.set_node_state(d[ATTR_NODE_UID], True),
    ),
    SERVICE_DISABLE_NODE: (
        {vol.Required(ATTR_NODE_UID): cv.string},
        lambda api, d: api.set_node_state(d[ATTR_NODE_UID], False),
    ),
    SERVICE_ENABLE_LIBRARY: (
        {vol.Required(ATTR_LIBRARY_UID): cv.string},
        lambda api, d: api.set_library_state(d[ATTR_LIBRARY_UID], True),
    ),
    SERVICE_DISABLE_LIBRARY: (
        {vol.Required(ATTR_LIBRARY_UID): cv.string},
        lambda api, d: api.set_library_state(d[ATTR_LIBRARY_UID], False),
    ),
    SERVICE_RESCAN_LIBRARY: (
        {vol.Required(ATTR_LIBRARY_UID): cv.string},
        lambda api, d: api.rescan_libraries([d[ATTR_LIBRARY_UID]]),
    ),
    SERVICE_RESCAN_ALL_LIBRARIES: ({}, lambda api, d: api.rescan_libraries()),
    SERVICE_ENABLE_FLOW: (
        {vol.Required(ATTR_FLOW_UID): cv.string},
        lambda api, d: api.set_flow_state(d[ATTR_FLOW_UID], True),
    ),
    SERVICE_DISABLE_FLOW: (
        {vol.Required(ATTR_FLOW_UID): cv.string},
        lambda api, d: api.set_flow_state(d[ATTR_FLOW_UID], False),
    ),
    SERVICE_REPROCESS_FILE: (
        {vol.Required(ATTR_FILE_UID): cv.string},
        lambda api, d: api.reprocess_files([d[ATTR_FILE_UID]]),
    ),
    SERVICE_FORCE_PROCESSING: (
        {vol.Required(ATTR_FILE_UID): UID_LIST},
        lambda api, d: api.force_processing(d[ATTR_FILE_UID]),
    ),
    SERVICE_UNHOLD_FILES: (
        {vol.Required(ATTR_FILE_UID): UID_LIST},
        lambda api, d: api.unhold_files(d[ATTR_FILE_UID]),
    ),
    SERVICE_ABORT_WORKER: (
        {vol.Required(ATTR_WORKER_UID): cv.string},
        lambda api, d: api.abort_worker(d[ATTR_WORKER_UID]),
    ),
    SERVICE_RUN_TASK: (
        {vol.Required(ATTR_TASK_UID): cv.string},
        lambda api, d: api.run_task(d[ATTR_TASK_UID]),
    ),
}


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the FileFlows services."""

    async def handle(call: ServiceCall) -> None:
        coordinator = _resolve_coordinator(hass, call)
        await coordinator.async_action(
            SERVICES[call.service][1](coordinator.api, call.data)
        )

    for service, (fields, _) in SERVICES.items():
        hass.services.async_register(
            DOMAIN,
            service,
            handle,
            schema=vol.Schema(
                {vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string, **fields}
            ),
        )
    return True


def _resolve_coordinator(
    hass: HomeAssistant, call: ServiceCall
) -> FileFlowsDataUpdateCoordinator:
    if entry_id := call.data.get(ATTR_CONFIG_ENTRY_ID):
        entry = hass.config_entries.async_get_entry(entry_id)
        if (
            entry is None
            or entry.domain != DOMAIN
            or entry.state is not ConfigEntryState.LOADED
        ):
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="entry_not_loaded",
                translation_placeholders={"entry_id": entry_id},
            )
        return entry.runtime_data
    entries = hass.config_entries.async_loaded_entries(DOMAIN)
    if len(entries) != 1:
        raise ServiceValidationError(
            translation_domain=DOMAIN, translation_key="entry_required"
        )
    return entries[0].runtime_data


async def async_setup_entry(hass: HomeAssistant, entry: FileFlowsConfigEntry) -> bool:
    """Set up FileFlows from a config entry."""
    data = entry.data
    if not data.get(CONF_API_TOKEN) and not data.get(CONF_FENRUS_TOKEN):
        raise ConfigEntryAuthFailed("API token required")
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
    coordinator = FileFlowsDataUpdateCoordinator(hass, entry, api)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: FileFlowsConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_migrate_entry(hass: HomeAssistant, entry: FileFlowsConfigEntry) -> bool:
    """Migrate old entries."""
    if entry.version > 2:
        return False
    if entry.version == 1:
        # The server no longer accepts username/password; setup starts reauth.
        data = {
            k: v for k, v in entry.data.items() if k not in ("username", "password")
        }
        hass.config_entries.async_update_entry(entry, data=data, version=2)
    return True
