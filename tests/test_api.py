"""Tests for the FileFlows API client."""

from __future__ import annotations

import hashlib
import hmac
import json
import re
from collections.abc import Callable

import aiohttp
import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
)

from custom_components.fileflows.api import (
    FileFlowsApi,
    FileFlowsApiDisabledError,
    FileFlowsApiError,
    FileFlowsAuthError,
    FileFlowsConnectionError,
    FileFlowsNotFoundError,
)

from .conftest import API_TOKEN, BASE, FENRUS, FENRUS_TOKEN, HOST


def _api(hass: HomeAssistant, api_token=API_TOKEN, fenrus_token=None) -> FileFlowsApi:
    return FileFlowsApi(
        async_get_clientsession(hass), HOST, 8585, False, api_token, fenrus_token
    )


def _expected_signature(
    method: str, path: str, headers: dict, body: bytes | None
) -> str:
    body_hash = hashlib.sha256(body).hexdigest() if body is not None else ""
    message = (
        f"{method}:{path}:{headers['X-Timestamp']}:{headers['X-Nonce']}:{body_hash}"
    )
    return hmac.new(API_TOKEN.encode(), message.encode(), hashlib.sha256).hexdigest()


async def test_bodiless_get_signature(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """A GET signs the path with an empty body hash."""
    aioclient_mock.get(f"{BASE}/api/status", json={"queue": 1})
    assert await _api(hass).get_status() == {"queue": 1}

    _, url, data, headers = aioclient_mock.mock_calls[0]
    assert data is None
    assert url.path == "/api/status"
    assert headers["X-Timestamp"].isdigit()
    assert re.fullmatch(r"[0-9a-f]{32}", headers["X-Nonce"])
    assert headers["X-Signature"] == _expected_signature(
        "GET", "/api/status", headers, None
    )
    assert "Authorization" not in headers


async def test_bodiless_pause_signature(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """Pause sends no body, so the query is unsigned and the body hash empty."""
    aioclient_mock.post(f"{BASE}/api/system/pause")
    await _api(hass).pause_system(5)

    _, url, data, headers = aioclient_mock.mock_calls[0]
    assert url.query == {"duration": "5", "abort": "false"}
    assert data is None
    assert "Content-Type" not in headers
    assert headers["X-Signature"] == _expected_signature(
        "POST", "/api/system/pause", headers, None
    )


@pytest.mark.parametrize(
    ("method", "path", "call"),
    [
        ("POST", "/api/library-file/unhold", lambda api: api.unhold_files(["a", "b"])),
        (
            "POST",
            "/api/library-file/force-processing",
            lambda api: api.force_processing(["a", "b"]),
        ),
        ("PUT", "/api/library/rescan", lambda api: api.rescan_libraries(["a", "b"])),
        ("DELETE", "/api/library-file/abort", lambda api: api.abort_worker("a")),
    ],
)
async def test_uids_body(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    method: str,
    path: str,
    call: Callable,
) -> None:
    """File and library uid writes send a signed {"Uids": [...]} body."""
    aioclient_mock.request(method, f"{BASE}{path}")
    await call(_api(hass))

    _, url, data, headers = aioclient_mock.mock_calls[0]
    assert url.path == path
    uids = ["a"] if path.endswith("abort") else ["a", "b"]
    assert json.loads(data) == {"Uids": uids}
    assert headers["Content-Type"] == "application/json"
    assert headers["X-Signature"] == _expected_signature(method, path, headers, data)


async def test_file_lists_use_list_all(
    hass: HomeAssistant, mock_server: Callable, aioclient_mock: AiohttpClientMocker
) -> None:
    """Running, upcoming and finished files come from list-all by status."""
    mock_server(
        {
            "/api/library-file/list-all?status=2&page=0": [{"Uid": "w1"}],
            "/api/library-file/list-all?status=0&page=0": [{"Uid": "u1"}],
            "/api/library-file/list-all?status=1&page=0": [{"Uid": "r1"}],
        }
    )
    data = await _api(hass).get_all_data()
    assert data["workers"] == [{"Uid": "w1"}]
    assert data["upcoming_files"] == [{"Uid": "u1"}]
    assert data["recently_finished"] == [{"Uid": "r1"}]

    calls = [c for c in aioclient_mock.mock_calls if c[1].path.endswith("/list-all")]
    assert sorted(c[1].query["status"] for c in calls) == ["0", "1", "2"]
    for _, url, _, headers in calls:
        assert url.query["page"] == "0"
        assert headers["X-Signature"] == _expected_signature(
            "GET", "/api/library-file/list-all", headers, None
        )


async def test_nonce_is_fresh(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """Every request gets its own nonce."""
    aioclient_mock.get(f"{BASE}/api/status", json={})
    api = _api(hass)
    await api.get_status()
    await api.get_status()
    nonces = {call[3]["X-Nonce"] for call in aioclient_mock.mock_calls}
    assert len(nonces) == 2


async def test_pause_indefinitely_and_resume(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """Pause without minutes must not send duration=0, which resumes."""
    aioclient_mock.post(f"{BASE}/api/system/pause")
    api = _api(hass)
    await api.pause_system()
    await api.resume_system()
    assert aioclient_mock.mock_calls[0][1].query["duration"] == "525600"
    assert aioclient_mock.mock_calls[1][1].query["duration"] == "0"


@pytest.mark.parametrize(
    ("kwargs", "error"),
    [
        ({"status": 401, "text": "Invalid signature"}, FileFlowsAuthError),
        ({"status": 401, "text": "The nonce has already been used"}, FileFlowsApiError),
        (
            {
                "status": 401,
                "text": "The request timestamp is too old, or the clocks are out of sync",
            },
            FileFlowsApiError,
        ),
        ({"status": 404}, FileFlowsNotFoundError),
        ({"status": 500}, FileFlowsApiError),
        (
            {"text": "<html></html>", "headers": {"Content-Type": "text/html"}},
            FileFlowsApiError,
        ),
        ({"text": "not json"}, FileFlowsApiError),
        ({"exc": TimeoutError()}, FileFlowsConnectionError),
        ({"exc": aiohttp.ClientConnectionError()}, FileFlowsConnectionError),
    ],
)
async def test_error_mapping(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    kwargs: dict,
    error: type[Exception],
) -> None:
    """HTTP failures map to typed errors."""
    aioclient_mock.get(f"{BASE}/api/status", **kwargs)
    with pytest.raises(error) as info:
        await _api(hass).get_status()
    if error is FileFlowsApiError:
        assert not isinstance(info.value, FileFlowsAuthError)


async def test_wrong_shape_and_empty_body(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """A list where a dict is expected is an error; an empty write body is fine."""
    aioclient_mock.get(f"{BASE}/api/status", json=[1])
    aioclient_mock.post(f"{BASE}/api/system/restart", text="")
    api = _api(hass)
    with pytest.raises(FileFlowsApiError):
        await api.get_status()
    await api.restart_system()


@pytest.mark.parametrize(
    ("uid", "raw_path", "signed_path"),
    [
        (
            "../restart",
            "/api/library/state/..%2Frestart",
            "/api/library/state/../restart",
        ),
        (
            "x?enable=true",
            "/api/library/state/x%3Fenable%3Dtrue",
            "/api/library/state/x?enable=true",
        ),
    ],
)
async def test_uid_is_quoted(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    uid: str,
    raw_path: str,
    signed_path: str,
) -> None:
    """User supplied uids cannot escape their path segment."""
    aioclient_mock.put(re.compile("/api/library/state/"))
    await _api(hass).set_library_state(uid, True)

    _, url, data, headers = aioclient_mock.mock_calls[0]
    assert url.raw_path == raw_path
    assert url.query == {"enable": "true"}
    assert headers["X-Signature"] == _expected_signature(
        "PUT", signed_path, headers, data
    )


async def test_library_file_status_normalized(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """The status list becomes a dict keyed by status name."""
    aioclient_mock.get(
        f"{BASE}/api/library-file/status",
        json=[
            {"Status": 4, "StatusCount": 3},
            {"Status": -1, "StatusCount": 2},
            {"Status": -3, "StatusCount": 5},
            {"Status": 7, "StatusCount": 9},
        ],
    )
    assert await _api(hass).get_library_file_status() == {
        "Disabled": 0,
        "OutOfSchedule": 2,
        "Unprocessed": 0,
        "Processed": 0,
        "Processing": 0,
        "Failed": 3,
        "OnHold": 5,
    }


async def test_fenrus_only(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """Without an API token only the webhook is queried, with its own header."""
    aioclient_mock.get(f"{BASE}/webhook/fenrus", json=FENRUS)
    api = _api(hass, api_token=None, fenrus_token=FENRUS_TOKEN)
    assert await api.get_all_data() == {"fenrus": FENRUS}
    headers = aioclient_mock.mock_calls[0][3]
    assert headers == {"X-Webhook-Token": FENRUS_TOKEN}
    with pytest.raises(FileFlowsAuthError):
        await api.restart_system()


async def test_validate_disabled(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """404 on validation means the API or webhook is switched off."""
    aioclient_mock.get(f"{BASE}/api/status", status=404)
    aioclient_mock.get(f"{BASE}/webhook/fenrus", status=404)
    with pytest.raises(FileFlowsApiDisabledError):
        await _api(hass).async_validate()
    with pytest.raises(FileFlowsApiDisabledError):
        await _api(hass, api_token=None, fenrus_token=FENRUS_TOKEN).async_validate()


@pytest.mark.parametrize(
    ("kwargs", "error"),
    [
        ({"status": 401, "text": "Invalid signature"}, FileFlowsAuthError),
        ({"exc": aiohttp.ClientConnectionError()}, FileFlowsConnectionError),
    ],
)
async def test_get_all_data_aborts_on_auth_and_connection(
    hass: HomeAssistant,
    mock_server: Callable,
    aioclient_mock: AiohttpClientMocker,
    kwargs: dict,
    error: type[Exception],
) -> None:
    """Auth and connection errors abort the refresh after every call finished."""
    mock_server(raw={"/api/settings": kwargs})
    with pytest.raises(error):
        await _api(hass).get_all_data()
    paths = {call[1].path for call in aioclient_mock.mock_calls}
    assert {"/api/settings", "/api/flow", "/api/system/version"} <= paths


@pytest.mark.parametrize(
    "kwargs",
    [
        {"status": 404},
        {"status": 500},
        {"text": "<html></html>", "headers": {"Content-Type": "text/html"}},
        {"text": "<!DOCTYPE html>"},
        {"json": [1, 2]},
    ],
    ids=["404", "500", "html-200", "html-no-type", "wrong-shape"],
)
async def test_optional_endpoint_failure_keeps_other_data(
    hass: HomeAssistant, mock_server: Callable, kwargs: dict
) -> None:
    """A broken optional endpoint only blanks its own key."""
    mock_server(raw={"/api/settings": kwargs})
    data = await _api(hass, fenrus_token=FENRUS_TOKEN).get_all_data()
    assert data["settings"] is None
    assert data["status"]["queue"] == 5
    assert data["fenrus"] == FENRUS
    assert data["nodes"][0]["Uid"] == "n1"
    assert data["libraries"][0]["Uid"] == "l1"
    assert data["library_file_status"]["Failed"] == 3
    assert data["version"] == "26.10.0"


@pytest.mark.parametrize(
    ("kwargs", "version"),
    [
        ({"text": "26.10", "headers": {"Content-Type": "text/plain"}}, "26.10"),
        (
            {"text": " 26.10.0\n", "headers": {"Content-Type": "text/plain"}},
            "26.10.0",
        ),
        ({"json": "26.10"}, "26.10"),
    ],
)
async def test_version_stays_text(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, kwargs: dict, version
) -> None:
    """A plain version is not parsed as a number."""
    aioclient_mock.get(f"{BASE}/api/system/version", **kwargs)
    assert await _api(hass).get_version() == version


async def test_ipv6_host(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """IPv6 hosts are bracketed in the URL."""
    aioclient_mock.get("http://[fd00::1]:8585/api/status", json={"queue": 1})
    api = FileFlowsApi(
        async_get_clientsession(hass), "fd00::1", 8585, False, API_TOKEN, None
    )
    assert await api.get_status() == {"queue": 1}


@pytest.mark.parametrize(
    ("kwargs", "error"),
    [
        ({"status": 401, "text": "Invalid token"}, FileFlowsAuthError),
        ({"status": 404}, FileFlowsApiDisabledError),
    ],
)
async def test_validate_checks_both_tokens(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    kwargs: dict,
    error: type[Exception],
) -> None:
    """With both tokens a bad Fenrus token fails validation too."""
    aioclient_mock.get(f"{BASE}/api/status", json={"queue": 0})
    aioclient_mock.get(f"{BASE}/webhook/fenrus", **kwargs)
    with pytest.raises(error):
        await _api(hass, fenrus_token=FENRUS_TOKEN).async_validate()
    assert [call[1].path for call in aioclient_mock.mock_calls] == [
        "/api/status",
        "/webhook/fenrus",
    ]


async def test_dead_server_fails_fast(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """A failing core call raises before any other endpoint is queried."""
    aioclient_mock.get(f"{BASE}/api/status", exc=aiohttp.ClientConnectionError())
    with pytest.raises(FileFlowsConnectionError):
        await _api(hass).get_all_data()
    assert aioclient_mock.call_count == 1
