"""Tests for FileFlows setup, coordinator, services and entities."""

from __future__ import annotations

from collections.abc import Callable
import re

import aiohttp
import pytest
import voluptuous as vol
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
)

from custom_components.fileflows.const import DOMAIN
from homeassistant.config_entries import SOURCE_REAUTH, ConfigEntryState
from homeassistant.const import (
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
    EntityCategory,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import (
    ConfigEntryAuthFailed,
    HomeAssistantError,
    ServiceValidationError,
)
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.update_coordinator import UpdateFailed

from .conftest import BASE, ENTRY_DATA, FENRUS, FENRUS_TOKEN, HOST, default_routes


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


def _writes(aioclient_mock: AiohttpClientMocker) -> list[tuple[str, str]]:
    return [
        (call[0].upper(), call[1].raw_path)
        for call in aioclient_mock.mock_calls
        if call[0].upper() != "GET"
    ]


async def test_setup_and_states(
    hass: HomeAssistant, mock_server: Callable, config_entry: MockConfigEntry
) -> None:
    """Entities reflect the API data with unchanged names."""
    await _setup(hass, config_entry)
    assert config_entry.state is ConfigEntryState.LOADED

    assert hass.states.get("sensor.fileflows_ff_local_queue_size").state == "5"
    assert hass.states.get("sensor.fileflows_ff_local_failed_files").state == "3"
    assert hass.states.get("sensor.fileflows_ff_local_files_on_hold").state == "2"
    assert hass.states.get("sensor.fileflows_ff_local_current_file").state == "a.mkv"
    assert hass.states.get("sensor.fileflows_ff_local_version").state == "26.10.0"
    assert hass.states.get("sensor.fileflows_ff_local_storage_saved").state == "0.0"
    assert (
        hass.states.get("sensor.fileflows_ff_local_storage_saved_percentage").state
        == "40.0"
    )
    assert hass.states.get("switch.fileflows_ff_local_node_main").state == STATE_ON
    assert hass.states.get("switch.fileflows_ff_local_flow_encode").state == STATE_OFF
    assert hass.states.get("binary_sensor.fileflows_ff_local_node_main_enabled")
    assert hass.states.get("button.fileflows_ff_local_rescan_movies")
    assert hass.states.get("button.fileflows_ff_local_run_task_cleanup")
    assert hass.states.get("button.fileflows_ff_local_pause_system")
    # no fenrus token: update state is unknown, nvidia endpoint 404 creates nothing
    assert (
        hass.states.get("binary_sensor.fileflows_ff_local_update_available").state
        == STATE_UNAVAILABLE
    )
    assert hass.states.get("sensor.fileflows_ff_local_nvidia_gpu_usage") is None

    device = dr.async_get(hass).async_get_device(
        identifiers={(DOMAIN, config_entry.entry_id)}
    )
    assert device.sw_version == "26.10.0"
    assert device.configuration_url == f"http://{HOST}:8585"


async def test_system_paused_polarity(
    hass: HomeAssistant, mock_server: Callable, config_entry: MockConfigEntry
) -> None:
    """system_paused is on while paused and the active switch is off."""
    await _setup(hass, config_entry)
    paused = hass.states.get("binary_sensor.fileflows_ff_local_system_paused")
    assert paused.state == STATE_ON
    assert "device_class" not in paused.attributes
    assert hass.states.get("switch.fileflows_ff_local_system_active").state == STATE_OFF

    mock_server({"/api/settings": {"IsPaused": False}})
    await config_entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    assert (
        hass.states.get("binary_sensor.fileflows_ff_local_system_paused").state
        == STATE_OFF
    )

    mock_server({"/api/settings": None})
    await config_entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    assert (
        hass.states.get("binary_sensor.fileflows_ff_local_system_paused").state
        == STATE_UNAVAILABLE
    )


async def test_fenrus_only_entities(hass: HomeAssistant, mock_server: Callable) -> None:
    """With only the webhook token, unknown values stay unavailable, not 0."""
    data = {k: v for k, v in ENTRY_DATA.items() if k != "api_token"}
    entry = MockConfigEntry(
        domain=DOMAIN, version=2, data={**data, "fenrus_token": FENRUS_TOKEN}
    )
    await _setup(hass, entry)
    assert entry.state is ConfigEntryState.LOADED
    assert hass.states.get("sensor.fileflows_ff_local_processed_files").state == "1234"
    assert hass.states.get("sensor.fileflows_ff_local_queue_size").state == "56"
    assert (
        hass.states.get("sensor.fileflows_ff_local_files_on_hold").state
        == STATE_UNAVAILABLE
    )
    assert (
        hass.states.get("sensor.fileflows_ff_local_version").state == STATE_UNAVAILABLE
    )
    assert (
        hass.states.get("binary_sensor.fileflows_ff_local_update_available").state
        == STATE_OFF
    )
    assert entry.runtime_data.storage_saved_bytes == 200000000000


@pytest.mark.parametrize("processing", [0, 1])
async def test_fenrus_only_current_file(
    hass: HomeAssistant, mock_server: Callable, processing: int
) -> None:
    """Without the API token the current file is unknown, never Idle."""
    mock_server({"/webhook/fenrus": {**FENRUS, "Processing": processing}})
    data = {k: v for k, v in ENTRY_DATA.items() if k != "api_token"}
    entry = MockConfigEntry(
        domain=DOMAIN, version=2, data={**data, "fenrus_token": FENRUS_TOKEN}
    )
    await _setup(hass, entry)
    assert (
        hass.states.get("sensor.fileflows_ff_local_current_file").state
        == STATE_UNAVAILABLE
    )


async def test_coordinator_errors(
    hass: HomeAssistant,
    mock_server: Callable,
    aioclient_mock: AiohttpClientMocker,
    config_entry: MockConfigEntry,
) -> None:
    """Connection errors fail the update, 401 starts reauth."""
    await _setup(hass, config_entry)
    coordinator = config_entry.runtime_data

    aioclient_mock.clear_requests()
    aioclient_mock.get(f"{BASE}/api/status", exc=aiohttp.ClientConnectionError())
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()

    aioclient_mock.clear_requests()
    aioclient_mock.get(f"{BASE}/api/status", status=401, text="Invalid signature")
    with pytest.raises(ConfigEntryAuthFailed):
        await coordinator._async_update_data()

    # clock skew is not a token problem and must not start reauth
    aioclient_mock.clear_requests()
    aioclient_mock.get(
        f"{BASE}/api/status", status=401, text="The request timestamp is too old"
    )
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()

    aioclient_mock.clear_requests()
    aioclient_mock.get(f"{BASE}/api/status", status=404)
    with pytest.raises(UpdateFailed, match="REST API is disabled or unlicensed"):
        await coordinator._async_update_data()


async def test_setup_retry_on_connection_error(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    config_entry: MockConfigEntry,
) -> None:
    """A dead server makes setup retry."""
    aioclient_mock.get(f"{BASE}/api/status", exc=aiohttp.ClientConnectionError())
    await _setup(hass, config_entry)
    assert config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_migrate_v1_starts_reauth(hass: HomeAssistant) -> None:
    """v1 username/password entries migrate and then ask for a token."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=1,
        data={
            "host": HOST,
            "port": 8585,
            "ssl": False,
            "verify_ssl": True,
            "username": "admin",
            "password": "pw",
        },
    )
    await _setup(hass, entry)
    assert entry.version == 2
    assert entry.data == {"host": HOST, "port": 8585, "ssl": False, "verify_ssl": True}
    assert entry.state is ConfigEntryState.SETUP_ERROR
    flows = hass.config_entries.flow.async_progress()
    assert [f["context"]["source"] for f in flows] == [SOURCE_REAUTH]


async def test_service_single_entry_implicit(
    hass: HomeAssistant,
    mock_server: Callable,
    aioclient_mock: AiohttpClientMocker,
    config_entry: MockConfigEntry,
) -> None:
    """With one entry the config_entry_id may be omitted."""
    await _setup(hass, config_entry)
    await hass.services.async_call(
        DOMAIN, "enable_node", {"node_uid": "n1"}, blocking=True
    )
    await hass.services.async_call(
        DOMAIN, "unhold_files", {"file_uid": "a"}, blocking=True
    )
    await hass.services.async_call(
        DOMAIN,
        "pause_system",
        {"config_entry_id": config_entry.entry_id, "minutes": 10},
        blocking=True,
    )
    assert _writes(aioclient_mock) == [
        ("PUT", "/api/agent/state/n1"),
        ("POST", "/api/library-file/unhold"),
        ("POST", "/api/system/pause"),
    ]
    unhold = next(c for c in aioclient_mock.mock_calls if c[1].path.endswith("unhold"))
    assert unhold[2] == b'{"Uids": ["a"]}'
    pause = next(c for c in aioclient_mock.mock_calls if c[1].path.endswith("pause"))
    assert pause[1].query["duration"] == "10"


async def test_service_unknown_or_unloaded_entry(
    hass: HomeAssistant, mock_server: Callable, config_entry: MockConfigEntry
) -> None:
    """An explicit config_entry_id must name a loaded FileFlows entry."""
    await _setup(hass, config_entry)
    unloaded = MockConfigEntry(domain=DOMAIN, version=2, data=dict(ENTRY_DATA))
    unloaded.add_to_hass(hass)
    for entry_id in ("nope", unloaded.entry_id):
        with pytest.raises(ServiceValidationError):
            await hass.services.async_call(
                DOMAIN,
                "run_task",
                {"task_uid": "t1", "config_entry_id": entry_id},
                blocking=True,
            )


@pytest.mark.parametrize(
    ("service", "path"),
    [
        ("force_processing", "/api/library-file/force-processing"),
        ("unhold_files", "/api/library-file/unhold"),
    ],
)
async def test_file_list_services(
    hass: HomeAssistant,
    mock_server: Callable,
    aioclient_mock: AiohttpClientMocker,
    config_entry: MockConfigEntry,
    service: str,
    path: str,
) -> None:
    """File uid lists are sent as a Uids object body."""
    await _setup(hass, config_entry)
    aioclient_mock.mock_calls.clear()
    await hass.services.async_call(
        DOMAIN, service, {"file_uid": ["a", "b"]}, blocking=True
    )
    call = next(c for c in aioclient_mock.mock_calls if c[0].upper() == "POST")
    assert call[1].path == path
    assert call[2] == b'{"Uids": ["a", "b"]}'


async def test_pause_minutes_validation(
    hass: HomeAssistant,
    mock_server: Callable,
    aioclient_mock: AiohttpClientMocker,
    config_entry: MockConfigEntry,
) -> None:
    """minutes=0 would resume, so the schema rejects it."""
    await _setup(hass, config_entry)
    aioclient_mock.mock_calls.clear()
    with pytest.raises(vol.Invalid):
        await hass.services.async_call(
            DOMAIN, "pause_system", {"minutes": 0}, blocking=True
        )
    assert _writes(aioclient_mock) == []
    await hass.services.async_call(DOMAIN, "pause_system", {}, blocking=True)
    pause = next(c for c in aioclient_mock.mock_calls if c[1].path.endswith("pause"))
    assert pause[1].query["duration"] == "525600"


async def test_fenrus_only_has_no_write_entities(
    hass: HomeAssistant, mock_server: Callable
) -> None:
    """Without an API token only the refresh button is created."""
    data = {k: v for k, v in ENTRY_DATA.items() if k != "api_token"}
    entry = MockConfigEntry(
        domain=DOMAIN, version=2, data={**data, "fenrus_token": FENRUS_TOKEN}
    )
    await _setup(hass, entry)
    entities = er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
    buttons = [e.unique_id for e in entities if e.domain == "button"]
    assert buttons == [f"{entry.entry_id}_refresh"]
    assert not [e for e in entities if e.domain == "switch"]


async def test_restart_button_disabled_by_default(
    hass: HomeAssistant, mock_server: Callable, config_entry: MockConfigEntry
) -> None:
    """Restart is a config entity that has to be enabled by hand."""
    await _setup(hass, config_entry)
    entry = er.async_get(hass).async_get("button.fileflows_ff_local_restart_server")
    assert entry.disabled_by is er.RegistryEntryDisabler.INTEGRATION
    assert entry.entity_category is EntityCategory.CONFIG
    assert hass.states.get("button.fileflows_ff_local_restart_server") is None


@pytest.mark.parametrize(
    ("entity_id", "suffix"),
    [
        ("sensor.fileflows_ff_local_queue_size", "queue_size"),
        ("binary_sensor.fileflows_ff_local_system_paused", "system_paused"),
        ("binary_sensor.fileflows_ff_local_node_main_enabled", "node_n1_enabled"),
        (
            "binary_sensor.fileflows_ff_local_library_movies_enabled",
            "library_l1_enabled",
        ),
        ("switch.fileflows_ff_local_system_active", "system_active"),
        ("switch.fileflows_ff_local_node_main", "node_n1"),
        ("switch.fileflows_ff_local_library_movies", "library_l1"),
        ("switch.fileflows_ff_local_flow_encode", "flow_f1"),
        ("button.fileflows_ff_local_pause_system", "pause"),
        ("button.fileflows_ff_local_rescan_movies", "rescan_l1"),
        ("button.fileflows_ff_local_run_task_cleanup", "task_t1"),
    ],
)
async def test_unique_ids_are_stable(
    hass: HomeAssistant,
    mock_server: Callable,
    config_entry: MockConfigEntry,
    entity_id: str,
    suffix: str,
) -> None:
    """Unique ids keep their format so existing registry entries survive."""
    await _setup(hass, config_entry)
    entry = er.async_get(hass).async_get(entity_id)
    assert entry.unique_id == f"{config_entry.entry_id}_{suffix}"


async def test_item_enabled_sensor_has_no_device_class(
    hass: HomeAssistant, mock_server: Callable, config_entry: MockConfigEntry
) -> None:
    """Enabled is not the same as running."""
    await _setup(hass, config_entry)
    state = hass.states.get("binary_sensor.fileflows_ff_local_node_main_enabled")
    assert state.state == STATE_ON
    assert "device_class" not in state.attributes


async def test_service_two_entries_need_id(
    hass: HomeAssistant, mock_server: Callable, config_entry: MockConfigEntry
) -> None:
    """With two loaded entries the target must be explicit."""
    await _setup(hass, config_entry)
    other = MockConfigEntry(
        domain=DOMAIN, version=2, data=dict(ENTRY_DATA), unique_id="other:8585"
    )
    await _setup(hass, other)
    assert other.state is ConfigEntryState.LOADED

    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(DOMAIN, "resume_system", {}, blocking=True)
    await hass.services.async_call(
        DOMAIN, "resume_system", {"config_entry_id": other.entry_id}, blocking=True
    )


async def test_service_api_failure(
    hass: HomeAssistant,
    mock_server: Callable,
    aioclient_mock: AiohttpClientMocker,
    config_entry: MockConfigEntry,
) -> None:
    """API failures in services surface as HomeAssistantError."""
    await _setup(hass, config_entry)
    aioclient_mock.clear_requests()
    aioclient_mock.post(re.compile("/api/"), status=500)
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            DOMAIN, "run_task", {"task_uid": "t1"}, blocking=True
        )


async def test_switch_and_button_failures(
    hass: HomeAssistant,
    mock_server: Callable,
    aioclient_mock: AiohttpClientMocker,
    config_entry: MockConfigEntry,
) -> None:
    """Failed actions raise HomeAssistantError instead of failing silently."""
    await _setup(hass, config_entry)
    aioclient_mock.clear_requests()
    aioclient_mock.put(re.compile("/api/"), status=500)
    aioclient_mock.post(re.compile("/api/"), status=500)
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            "switch",
            "turn_off",
            {"entity_id": "switch.fileflows_ff_local_node_main"},
            blocking=True,
        )
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            "button",
            "press",
            {"entity_id": "button.fileflows_ff_local_rescan_movies"},
            blocking=True,
        )


async def test_dynamic_and_removed_items(
    hass: HomeAssistant, mock_server: Callable, config_entry: MockConfigEntry
) -> None:
    """New agents get entities; vanished ones become unavailable."""
    await _setup(hass, config_entry)
    assert hass.states.get("switch.fileflows_ff_local_node_second") is None

    agents = [
        *default_routes()["/api/agent"],
        {"Uid": "n2", "Name": "Second", "Enabled": False},
    ]
    mock_server({"/api/agent": agents})
    await config_entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get("switch.fileflows_ff_local_node_second").state == STATE_OFF

    mock_server({"/api/agent": agents[1:]})
    await config_entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    assert (
        hass.states.get("switch.fileflows_ff_local_node_main").state
        == STATE_UNAVAILABLE
    )
    assert hass.states.get("switch.fileflows_ff_local_node_second").state == STATE_OFF


async def test_version_change_updates_device(
    hass: HomeAssistant, mock_server: Callable, config_entry: MockConfigEntry
) -> None:
    """A server upgrade is reflected in the device registry."""
    await _setup(hass, config_entry)
    mock_server(version="26.11.0")
    await config_entry.runtime_data.async_refresh()
    device = dr.async_get(hass).async_get_device(
        identifiers={(DOMAIN, config_entry.entry_id)}
    )
    assert device.sw_version == "26.11.0"


async def test_unload_keeps_services(
    hass: HomeAssistant, mock_server: Callable, config_entry: MockConfigEntry
) -> None:
    """Services stay registered after unload."""
    await _setup(hass, config_entry)
    assert await hass.config_entries.async_unload(config_entry.entry_id)
    assert config_entry.state is ConfigEntryState.NOT_LOADED
    assert hass.services.has_service(DOMAIN, "pause_system")
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(DOMAIN, "pause_system", {}, blocking=True)


async def test_restored_attributes(
    hass: HomeAssistant, mock_server: Callable, config_entry: MockConfigEntry
) -> None:
    """Attributes older dashboards read are still there."""
    await _setup(hass, config_entry)
    current = hass.states.get("sensor.fileflows_ff_local_current_file").attributes
    assert current["processing_time"] == "1h"
    assert current["details"] == [
        {
            "file": "a.mkv",
            "library": "Movies",
            "step": "Encode",
            "progress": 42,
        }
    ]
    workers = hass.states.get("sensor.fileflows_ff_local_active_workers").attributes
    assert workers["total_runners"] == 2
    assert workers["workers"] == []


async def test_file_and_worker_uids(
    hass: HomeAssistant, mock_server: Callable, config_entry: MockConfigEntry
) -> None:
    """File lists and running workers expose the uids the services need."""
    mock_server(
        {
            "/api/library-file/list-all?status=2&page=0": [
                {"Uid": "w1", "DisplayName": "a.mkv", "AgentName": "Main"},
                {"Uid": "w2", "DisplayName": "b.mkv", "AgentName": None},
            ],
            "/api/library-file/list-all?status=0&page=0": [
                {"Uid": "u1", "DisplayName": "c.mkv", "LibraryName": "Movies"}
            ],
            "/api/library-file/list-all?status=1&page=0": [
                {"Uid": "r1", "DisplayName": "d.mkv", "LibraryName": "TV"}
            ],
        }
    )
    await _setup(hass, config_entry)

    def attrs(name: str) -> dict:
        return hass.states.get(f"sensor.fileflows_ff_local_{name}").attributes

    assert "uid" not in attrs("processing_files")["files"][0]
    assert attrs("upcoming_files")["files"] == [
        {"name": "c.mkv", "library": "Movies", "uid": "u1"}
    ]
    assert attrs("recently_finished")["files"] == [
        {"name": "d.mkv", "library": "TV", "uid": "r1"}
    ]
    assert attrs("active_workers")["workers"] == [
        {"uid": "w1", "file": "a.mkv", "agent": "Main"},
        {"uid": "w2", "file": "b.mkv", "agent": None},
    ]


async def test_ipv6_configuration_url(
    hass: HomeAssistant, mock_server: Callable
) -> None:
    """The device link brackets an IPv6 host."""
    base = "http://[fd00::1]:8585"
    mock_server(base=base)
    entry = MockConfigEntry(
        domain=DOMAIN, version=2, data={**ENTRY_DATA, "host": "fd00::1"}
    )
    await _setup(hass, entry)
    device = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, entry.entry_id)})
    assert device.configuration_url == base


async def test_reconfigure_renames_entry_and_device(
    hass: HomeAssistant, mock_server: Callable, config_entry: MockConfigEntry
) -> None:
    """A new host shows up in the entry title and device name."""
    await _setup(hass, config_entry)
    mock_server(base="http://elsewhere:9000")
    result = await config_entry.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {**ENTRY_DATA, "host": "elsewhere", "port": 9000}
    )
    await hass.async_block_till_done()
    assert result["reason"] == "reconfigure_successful"
    assert config_entry.title == "FileFlows (elsewhere)"
    assert config_entry.state is ConfigEntryState.LOADED
    device = dr.async_get(hass).async_get_device(
        identifiers={(DOMAIN, config_entry.entry_id)}
    )
    assert device.name == "FileFlows (elsewhere)"
    assert device.configuration_url == "http://elsewhere:9000"
