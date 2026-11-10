"""Tests for the values the FileFlows coordinator derives from API data."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.fileflows.const import DOMAIN
from custom_components.fileflows.coordinator import FileFlowsDataUpdateCoordinator

from .conftest import ENTRY_DATA, FENRUS, FENRUS_TOKEN, default_routes

STATUS = default_routes()["/api/status"]


async def _coordinator(
    hass: HomeAssistant,
    mock_server: Callable,
    overrides: dict[str, Any],
    data: dict[str, Any],
) -> FileFlowsDataUpdateCoordinator:
    mock_server(overrides)
    entry = MockConfigEntry(domain=DOMAIN, version=2, data=data)
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry.runtime_data


def _series(labels, items, final, savings) -> dict[str, Any]:
    return {
        "labels": labels,
        "items": items,
        "series": [
            {"name": "Final Size", "data": final},
            {"name": "Savings", "data": savings},
        ],
    }


FENRUS_ONLY = {
    **{k: v for k, v in ENTRY_DATA.items() if k != "api_token"},
    "fenrus_token": FENRUS_TOKEN,
}
BOTH_TOKENS = {**ENTRY_DATA, "fenrus_token": FENRUS_TOKEN}


@pytest.mark.parametrize(
    ("data", "overrides", "saved", "percent", "by_library"),
    [
        pytest.param(
            FENRUS_ONLY,
            {},
            200000000000,
            40.0,
            [
                {
                    "library": "Movies",
                    "items": 100,
                    "final": 300000000000,
                    "saved": 200000000000,
                }
            ],
            id="fenrus",
        ),
        pytest.param(
            ENTRY_DATA,
            {
                "/api/statistics/storage-saved": _series(
                    ["Movies", "TV", "Total"],
                    [1, 2, 3],
                    [100, 200, 300],
                    [50, None, 50],
                )
            },
            50,
            14.3,
            [
                {"library": "Movies", "items": 1, "final": 100, "saved": 50},
                {"library": "TV", "items": 2, "final": 200, "saved": 0},
            ],
            id="series-total",
        ),
        pytest.param(
            ENTRY_DATA,
            {"/api/statistics/storage-saved": _series(["Movies"], [1], [100], [50])},
            None,
            None,
            [{"library": "Movies", "items": 1, "final": 100, "saved": 50}],
            id="missing-total",
        ),
        pytest.param(
            ENTRY_DATA,
            {
                "/api/statistics/storage-saved": {
                    "labels": ["Movies", "Total"],
                    "items": None,
                    "series": [None, {"name": "Savings", "data": None}],
                }
            },
            0,
            None,
            [{"library": "Movies", "items": 0, "final": 0, "saved": 0}],
            id="null-entries",
        ),
        pytest.param(
            ENTRY_DATA,
            {
                "/api/statistics/storage-saved": _series(
                    ["Movies", "Total"], [0, 0], [0, 0], [0, 0]
                )
            },
            0,
            None,
            [{"library": "Movies", "items": 0, "final": 0, "saved": 0}],
            id="zero-original",
        ),
        pytest.param(
            ENTRY_DATA,
            {"/api/statistics/storage-saved": None},
            None,
            None,
            None,
            id="absent",
        ),
    ],
)
async def test_storage_math(
    hass: HomeAssistant,
    mock_server: Callable,
    data: dict[str, Any],
    overrides: dict[str, Any],
    saved: int | None,
    percent: float | None,
    by_library: list[dict[str, Any]] | None,
) -> None:
    """Savings come from Fenrus or the statistics series, never as a fake 0 %."""
    coordinator = await _coordinator(hass, mock_server, overrides, data)
    assert coordinator.storage_saved_bytes == saved
    assert coordinator.storage_saved_percent == percent
    assert coordinator.storage_saved_by_library == by_library


@pytest.mark.parametrize(
    ("data", "overrides", "queue_size", "unprocessed"),
    [
        pytest.param(ENTRY_DATA, {}, 5, 0, id="status-queue-and-file-status"),
        pytest.param(
            ENTRY_DATA,
            {
                "/api/status": {**STATUS, "queue": None},
                "/api/library-file/status": [{"Status": 0, "StatusCount": 7}],
            },
            7,
            7,
            id="null-queue-uses-file-status",
        ),
        pytest.param(
            ENTRY_DATA,
            {"/api/library-file/status": None},
            5,
            5,
            id="no-file-status-uses-queue",
        ),
        pytest.param(
            ENTRY_DATA,
            {
                "/api/status": {k: v for k, v in STATUS.items() if k != "queue"},
                "/api/library-file/status": None,
            },
            None,
            None,
            id="nothing",
        ),
        pytest.param(
            BOTH_TOKENS,
            {
                "/api/status": {**STATUS, "queue": None},
                "/api/library-file/status": None,
            },
            56,
            56,
            id="fenrus",
        ),
        pytest.param(
            BOTH_TOKENS,
            {
                "/api/library-file/status": None,
                "/webhook/fenrus": {**FENRUS, "Unprocessed": None},
            },
            5,
            5,
            id="null-fenrus-uses-queue",
        ),
        pytest.param(FENRUS_ONLY, {}, 56, 56, id="fenrus-only"),
    ],
)
async def test_count_fallbacks(
    hass: HomeAssistant,
    mock_server: Callable,
    data: dict[str, Any],
    overrides: dict[str, Any],
    queue_size: int | None,
    unprocessed: int | None,
) -> None:
    """Present-but-null counts fall through to the next source."""
    coordinator = await _coordinator(hass, mock_server, overrides, data)
    assert coordinator.queue_size == queue_size
    assert coordinator.files_unprocessed == unprocessed


async def test_processing_files_only_dicts(
    hass: HomeAssistant, mock_server: Callable
) -> None:
    """Junk entries in processingFiles are dropped."""
    first = STATUS["processingFiles"][0]
    coordinator = await _coordinator(
        hass,
        mock_server,
        {"/api/status": {**STATUS, "processingFiles": ["x", None, first]}},
        ENTRY_DATA,
    )
    assert coordinator.processing_files == [first]
    assert coordinator.current_file == "a.mkv"
