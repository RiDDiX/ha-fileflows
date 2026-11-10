"""Fixtures for FileFlows tests."""

from __future__ import annotations

from collections.abc import Callable
import re
from typing import Any

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
)

from custom_components.fileflows.const import DOMAIN

HOST = "ff.local"
BASE = f"http://{HOST}:8585"
API_TOKEN = "secret-token"
FENRUS_TOKEN = "fenrus-token"

ENTRY_DATA = {
    "host": HOST,
    "port": 8585,
    "ssl": False,
    "verify_ssl": True,
    "api_token": API_TOKEN,
}

FENRUS = {
    "Processing": 1,
    "Failed": 0,
    "Disabled": 0,
    "OutOfSchedule": 0,
    "Processed": 1234,
    "Unprocessed": 56,
    "UpdateAvailable": False,
    "Libraries": [
        {
            "Library": "Movies",
            "TotalFiles": 100,
            "OriginalSize": 500000000000,
            "FinalSize": 300000000000,
        }
    ],
}


def default_routes() -> dict[str, Any]:
    """Return JSON bodies for every GET route, None meaning 404."""
    return {
        "/api/status": {
            "queue": 5,
            "processing": 1,
            "processed": 100,
            "time": "1h",
            "processingFiles": [
                {
                    "name": "a.mkv",
                    "library": "Movies",
                    "step": "Encode",
                    "stepPercent": 42,
                }
            ],
        },
        "/api/settings": {"IsPaused": True},
        "/api/agent": [
            {"Uid": "n1", "Name": "Main", "Enabled": True, "FlowRunners": 2}
        ],
        "/api/library": [{"Uid": "l1", "Name": "Movies", "Enabled": True}],
        "/api/flow": [{"Uid": "f1", "Name": "Encode", "Enabled": False}],
        "/api/task": [{"Uid": "t1", "Name": "Cleanup"}],
        "/api/plugin": [],
        "/api/library-file/list-all?status=2&page=0": [],
        "/api/library-file/list-all?status=0&page=0": [],
        "/api/library-file/list-all?status=1&page=0": [],
        "/api/library-file/status": [
            {"Status": 4, "StatusCount": 3},
            {"Status": -3, "StatusCount": 2},
        ],
        "/api/statistics/storage-saved": {
            "labels": ["Movies", "Total"],
            "items": [10, 10],
            "series": [
                {"name": "Final Size", "data": [300, 300]},
                {"name": "Savings", "data": [None, 200]},
            ],
        },
        "/api/nvidia/smi": None,
        "/webhook/fenrus": FENRUS,
    }


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable loading the integration from custom_components."""


@pytest.fixture
def mock_server(
    aioclient_mock: AiohttpClientMocker,
) -> Callable[..., None]:
    """Register FileFlows routes; overrides replace single routes.

    raw maps a path to aioclient_mock kwargs and wins over the JSON routes.
    """

    def register(
        overrides: dict[str, Any] | None = None,
        version: str = "26.10.0",
        raw: dict[str, dict[str, Any]] | None = None,
        base: str = BASE,
    ) -> None:
        aioclient_mock.clear_requests()
        for path, kwargs in (raw or {}).items():
            aioclient_mock.get(f"{base}{path}", **kwargs)
        routes = default_routes() | (overrides or {})
        for path, body in routes.items():
            if body is None:
                aioclient_mock.get(f"{base}{path}", status=404)
            else:
                aioclient_mock.get(f"{base}{path}", json=body)
        aioclient_mock.get(
            f"{base}/api/system/version",
            text=version,
            headers={"Content-Type": "text/plain"},
        )
        for method in ("put", "post", "delete"):
            aioclient_mock.request(method, re.compile(f"{re.escape(base)}/api/"))

    register()
    return register


@pytest.fixture
def config_entry() -> MockConfigEntry:
    """Return a config entry with an API token."""
    return MockConfigEntry(
        domain=DOMAIN,
        version=2,
        title=f"FileFlows ({HOST})",
        data=dict(ENTRY_DATA),
        unique_id=f"{HOST}:8585",
    )
