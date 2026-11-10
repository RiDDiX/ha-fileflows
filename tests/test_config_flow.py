"""Tests for the FileFlows config flow."""

from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
from unittest.mock import patch

import aiohttp
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
)

from custom_components.fileflows.const import DOMAIN
from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from .conftest import API_TOKEN, BASE, ENTRY_DATA, FENRUS_TOKEN, HOST

USER_INPUT = {**ENTRY_DATA}


@pytest.fixture
def no_setup():
    """Skip entry setup after the flow creates an entry."""
    with patch("custom_components.fileflows.async_setup_entry", return_value=True):
        yield


async def _user_flow(hass: HomeAssistant, user_input: dict) -> dict:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    return await hass.config_entries.flow.async_configure(result["flow_id"], user_input)


async def test_user_success(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, no_setup: None
) -> None:
    """A working API token creates the entry."""
    aioclient_mock.get(f"{BASE}/api/status", json={"queue": 0})
    result = await _user_flow(hass, USER_INPUT)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == f"FileFlows ({HOST})"
    assert result["data"] == {**ENTRY_DATA, "fenrus_token": None}
    assert result["result"].unique_id == f"{HOST}:8585"


async def test_user_no_token(hass: HomeAssistant) -> None:
    """At least one token is required."""
    data = {k: v for k, v in USER_INPUT.items() if k != "api_token"}
    result = await _user_flow(hass, data)
    assert result["errors"] == {"base": "no_token"}


@pytest.mark.parametrize(
    ("kwargs", "error"),
    [
        ({"status": 401, "text": "Invalid signature"}, "invalid_auth"),
        ({"status": 404}, "api_disabled"),
        ({"exc": aiohttp.ClientConnectionError()}, "cannot_connect"),
        ({"status": 500}, "cannot_connect"),
    ],
)
async def test_user_errors(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, kwargs: dict, error: str
) -> None:
    """Validation failures map to form errors."""
    aioclient_mock.get(f"{BASE}/api/status", **kwargs)
    result = await _user_flow(hass, USER_INPUT)
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": error}


async def test_user_unknown_error(hass: HomeAssistant) -> None:
    """Unexpected exceptions map to unknown."""
    with patch(
        "custom_components.fileflows.config_flow.FileFlowsApi.async_validate",
        side_effect=RuntimeError,
    ):
        result = await _user_flow(hass, USER_INPUT)
    assert result["errors"] == {"base": "unknown"}


async def test_user_duplicate(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    """The same host and port cannot be added twice."""
    config_entry.add_to_hass(hass)
    result = await _user_flow(hass, USER_INPUT)
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_reauth(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    config_entry: MockConfigEntry,
    no_setup: None,
) -> None:
    """Reauth stores the new tokens."""
    config_entry.add_to_hass(hass)
    aioclient_mock.get(f"{BASE}/api/status", json={})
    result = await config_entry.start_reauth_flow(hass)
    assert result["step_id"] == "reauth_confirm"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"api_token": "new-token"}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert config_entry.data["api_token"] == "new-token"


async def test_reauth_requires_token(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    """Reauth without any token shows no_token."""
    config_entry.add_to_hass(hass)
    result = await config_entry.start_reauth_flow(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["errors"] == {"base": "no_token"}


async def test_reconfigure(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    config_entry: MockConfigEntry,
    no_setup: None,
) -> None:
    """Reconfigure updates settings on the same server."""
    config_entry.add_to_hass(hass)
    aioclient_mock.get(f"{BASE}/api/status", json={})
    result = await config_entry.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {**USER_INPUT, "verify_ssl": False}
    )
    assert result["reason"] == "reconfigure_successful"
    assert config_entry.data["verify_ssl"] is False
    assert config_entry.unique_id == f"{HOST}:8585"


async def test_reconfigure_host_change(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    config_entry: MockConfigEntry,
    no_setup: None,
) -> None:
    """A moved server keeps its entry and gets a new unique_id."""
    config_entry.add_to_hass(hass)
    aioclient_mock.get("http://elsewhere:9000/api/status", json={})
    result = await config_entry.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {**USER_INPUT, "host": "elsewhere", "port": 9000}
    )
    assert result["reason"] == "reconfigure_successful"
    assert config_entry.unique_id == "elsewhere:9000"
    assert config_entry.data["host"] == "elsewhere"
    assert config_entry.data["port"] == 9000


async def test_reconfigure_collision(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    """Moving onto a server that already has an entry aborts."""
    config_entry.add_to_hass(hass)
    MockConfigEntry(
        domain=DOMAIN,
        version=2,
        data={**ENTRY_DATA, "host": "elsewhere"},
        unique_id="elsewhere:8585",
    ).add_to_hass(hass)
    result = await config_entry.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {**USER_INPUT, "host": "elsewhere"}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert config_entry.unique_id == f"{HOST}:8585"
    assert config_entry.data["host"] == HOST


async def test_user_host_stripped(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, no_setup: None
) -> None:
    """Whitespace around the host is dropped before it is used or stored."""
    aioclient_mock.get(f"{BASE}/api/status", json={"queue": 0})
    result = await _user_flow(hass, {**USER_INPUT, "host": f"  {HOST} "})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["host"] == HOST
    assert result["result"].unique_id == f"{HOST}:8585"


@pytest.mark.parametrize(
    "host", ["http://ff.local", "ff.local/fileflows", "ff local", "   "]
)
async def test_user_invalid_host(hass: HomeAssistant, host: str) -> None:
    """Hosts that cannot form a URL are rejected on the host field."""
    result = await _user_flow(hass, {**USER_INPUT, "host": host})
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"host": "invalid_host"}


@pytest.mark.parametrize(
    ("kwargs", "error"),
    [
        ({"status": 401, "text": "Invalid token"}, "invalid_auth"),
        ({"status": 404}, "api_disabled"),
    ],
)
async def test_user_bad_fenrus_token(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, kwargs: dict, error: str
) -> None:
    """With both tokens set, the Fenrus token is validated as well."""
    aioclient_mock.get(f"{BASE}/api/status", json={"queue": 0})
    aioclient_mock.get(f"{BASE}/webhook/fenrus", **kwargs)
    result = await _user_flow(hass, {**USER_INPUT, "fenrus_token": FENRUS_TOKEN})
    assert result["errors"] == {"base": error}


@pytest.mark.parametrize(
    ("kwargs", "error"),
    [
        ({"status": 401, "text": "Invalid signature"}, "invalid_auth"),
        ({"status": 404}, "api_disabled"),
    ],
)
async def test_reauth_errors(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    config_entry: MockConfigEntry,
    kwargs: dict,
    error: str,
) -> None:
    """Reauth keeps the old token and shows the validation error."""
    config_entry.add_to_hass(hass)
    aioclient_mock.get(f"{BASE}/api/status", **kwargs)
    result = await config_entry.start_reauth_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"api_token": "new-token"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": error}
    assert config_entry.data["api_token"] == API_TOKEN


async def test_options_flow_sets_scan_interval(
    hass: HomeAssistant, mock_server: Callable, config_entry: MockConfigEntry
) -> None:
    """The scan interval is saved and used by the coordinator after reload."""
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.runtime_data.update_interval == timedelta(seconds=30)

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"scan_interval": 120}
    )
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert config_entry.options == {"scan_interval": 120}
    assert config_entry.runtime_data.update_interval == timedelta(seconds=120)
    assert API_TOKEN == config_entry.data["api_token"]
