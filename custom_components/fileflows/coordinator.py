"""DataUpdateCoordinator for FileFlows."""

from __future__ import annotations

import logging
from collections.abc import Awaitable
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    FileFlowsApi,
    FileFlowsApiError,
    FileFlowsAuthError,
    FileFlowsNotFoundError,
)
from .const import CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

type FileFlowsConfigEntry = ConfigEntry[FileFlowsDataUpdateCoordinator]

INDEXED = ("nodes", "libraries", "flows", "tasks")
GIB = 1024**3


class FileFlowsDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching FileFlows data."""

    config_entry: FileFlowsConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: FileFlowsConfigEntry, api: FileFlowsApi
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(
                seconds=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
            ),
        )
        self.api = api

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from API."""
        previous_version = self.version
        try:
            data = await self.api.get_all_data()
        except FileFlowsAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except FileFlowsNotFoundError as err:
            endpoint = "REST API" if self.api.has_api else "Fenrus endpoint"
            raise UpdateFailed(
                f"The FileFlows {endpoint} is disabled or unlicensed: {err}"
            ) from err
        except FileFlowsApiError as err:
            raise UpdateFailed(f"Error communicating with FileFlows: {err}") from err
        data["index"] = {
            kind: {
                item["Uid"]: item for item in data.get(kind) or [] if item.get("Uid")
            }
            for kind in INDEXED
        }
        version = data.get("version")
        if self.data and version and version != previous_version:
            registry = dr.async_get(self.hass)
            device = registry.async_get_device(
                identifiers={(DOMAIN, self.config_entry.entry_id)}
            )
            if device:
                registry.async_update_device(device.id, sw_version=version)
        return data

    async def async_action(self, call: Awaitable[Any]) -> None:
        """Run a write call, surface failures to the user and refresh."""
        try:
            await call
        except FileFlowsApiError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="api_error",
                translation_placeholders={"error": str(err)},
            ) from err
        await self.async_request_refresh()

    def _get(self, key: str) -> Any:
        return self.data.get(key) if self.data else None

    def item(self, kind: str, uid: str) -> dict[str, Any] | None:
        """Return a node, library, flow or task by Uid."""
        return self.index(kind).get(uid)

    def index(self, kind: str) -> dict[str, dict[str, Any]]:
        """Return the items of one kind keyed by Uid."""
        return self._get("index").get(kind, {}) if self.data else {}

    # Status

    @property
    def status(self) -> dict[str, Any] | None:
        """Return /api/status data."""
        return self._get("status")

    @property
    def fenrus(self) -> dict[str, Any] | None:
        """Return /webhook/fenrus data."""
        return self._get("fenrus")

    @property
    def is_paused(self) -> bool | None:
        """Return whether processing is paused."""
        settings = self._get("settings")
        return settings.get("IsPaused") if settings else None

    @property
    def version(self) -> str | None:
        """Return the server version."""
        return self._get("version")

    @property
    def update_available(self) -> bool | None:
        """Return whether an update is available."""
        return self.fenrus.get("UpdateAvailable") if self.fenrus else None

    @property
    def processing_time(self) -> str | None:
        """Return the processing time reported by the server."""
        return self.status.get("time") if self.status else None

    @property
    def processing_files(self) -> list[dict[str, Any]] | None:
        """Return the files being processed right now."""
        files = self.status.get("processingFiles") if self.status else None
        if not isinstance(files, list):
            return None
        return [f for f in files if isinstance(f, dict)]

    # Counts

    def _count(
        self, name: str, status_key: str | None = None, *, status_first: bool = True
    ) -> int | None:
        """Return the first non-null count from status, file status and fenrus."""
        sources = [(self._get("library_file_status"), name), (self.fenrus, name)]
        if status_key:
            sources.insert(
                0 if status_first else len(sources), (self.status, status_key)
            )
        for source, key in sources:
            if source and (value := source.get(key)) is not None:
                return value
        return None

    @property
    def files_unprocessed(self) -> int | None:
        """Return the number of unprocessed files."""
        return self._count("Unprocessed", "queue", status_first=False)

    @property
    def files_processed(self) -> int | None:
        """Return the number of processed files."""
        return self._count("Processed", "processed")

    @property
    def files_processing(self) -> int | None:
        """Return the number of files being processed."""
        return self._count("Processing", "processing")

    @property
    def files_failed(self) -> int | None:
        """Return the number of failed files."""
        return self._count("Failed")

    @property
    def files_on_hold(self) -> int | None:
        """Return the number of files on hold."""
        return self._count("OnHold")

    @property
    def files_out_of_schedule(self) -> int | None:
        """Return the number of files out of schedule."""
        return self._count("OutOfSchedule")

    @property
    def queue_size(self) -> int | None:
        """Return the queue size."""
        return self._count("Unprocessed", "queue")

    # Workers

    @property
    def workers(self) -> list[dict[str, Any]] | None:
        """Return running workers."""
        return self._get("workers")

    @property
    def active_workers(self) -> int | None:
        """Return the number of active workers."""
        if self.processing_files:
            return len(self.processing_files)
        if self.workers is not None:
            return len(self.workers)
        return None if self.processing_files is None else 0

    @property
    def is_processing(self) -> bool | None:
        """Return whether any file is being processed."""
        if self.processing_files:
            return True
        if (processing := self.files_processing) is not None:
            return processing > 0
        return None if self.workers is None else bool(self.workers)

    def _current(self, key: str) -> Any:
        return self.processing_files[0].get(key) if self.processing_files else None

    @property
    def current_file(self) -> str | None:
        """Return the name of the file being processed."""
        if self.processing_files:
            first = self.processing_files[0]
            return first.get("name") or first.get("relativePath")
        return self.workers[0].get("DisplayName") if self.workers else None

    @property
    def current_file_progress(self) -> float | None:
        """Return the progress of the current file."""
        return self._current("stepPercent")

    @property
    def current_step(self) -> str | None:
        """Return the current processing step."""
        return self._current("step")

    # Lists

    @property
    def nodes(self) -> list[dict[str, Any]] | None:
        """Return processing agents."""
        return self._get("nodes")

    @property
    def libraries(self) -> list[dict[str, Any]] | None:
        """Return libraries."""
        return self._get("libraries")

    @property
    def flows(self) -> list[dict[str, Any]] | None:
        """Return flows."""
        return self._get("flows")

    @property
    def tasks(self) -> list[dict[str, Any]] | None:
        """Return scheduled tasks."""
        return self._get("tasks")

    @property
    def plugins(self) -> list[dict[str, Any]] | None:
        """Return plugins."""
        return self._get("plugins")

    @property
    def upcoming_files(self) -> list[dict[str, Any]] | None:
        """Return the next files to process."""
        return self._get("upcoming_files")

    @property
    def recently_finished(self) -> list[dict[str, Any]] | None:
        """Return recently finished files."""
        return self._get("recently_finished")

    @property
    def enabled_nodes_count(self) -> int | None:
        """Return the number of enabled agents."""
        return enabled_count(self.nodes)

    @property
    def total_runners(self) -> int | None:
        """Return the runners of all enabled agents."""
        if self.nodes is None:
            return None
        return sum(n.get("FlowRunners") or 0 for n in self.nodes if n.get("Enabled"))

    # Storage

    def _storage(self) -> tuple[list[dict[str, Any]], dict[str, Any] | None] | None:
        """Return per-library rows and the total row."""
        if self.fenrus and isinstance(libraries := self.fenrus.get("Libraries"), list):
            rows = [
                {
                    "library": lib.get("Library"),
                    "items": lib.get("TotalFiles"),
                    "final": lib.get("FinalSize") or 0,
                    "saved": (lib.get("OriginalSize") or 0)
                    - (lib.get("FinalSize") or 0),
                }
                for lib in libraries
                if isinstance(lib, dict)
            ]
            total = {
                "final": sum(r["final"] for r in rows),
                "saved": sum(r["saved"] for r in rows),
            }
            return rows, total
        stats = self._get("storage_saved")
        if not stats:
            return None
        series = {
            s.get("name"): s.get("data") or []
            for s in stats.get("series") or []
            if isinstance(s, dict)
        }
        items = stats.get("items") or []

        def at(values: list[Any], i: int) -> Any:
            return (values[i] if i < len(values) else None) or 0

        rows = [
            {
                "library": label,
                "items": at(items, i),
                "final": at(series.get("Final Size", []), i),
                "saved": at(series.get("Savings", []), i),
            }
            for i, label in enumerate(stats.get("labels") or [])
        ]
        total = next((r for r in rows if r["library"] == "Total"), None)
        return [r for r in rows if r is not total], total

    @property
    def storage_saved_bytes(self) -> int | None:
        """Return the total bytes saved."""
        storage = self._storage()
        return storage[1]["saved"] if storage and storage[1] else None

    @property
    def storage_saved_gb(self) -> float | None:
        """Return the total storage saved in GB."""
        saved = self.storage_saved_bytes
        return None if saved is None else round(saved / GIB, 2)

    @property
    def storage_saved_percent(self) -> float | None:
        """Return the storage saved as a percentage of the original size."""
        storage = self._storage()
        if not storage or not storage[1]:
            return None
        original = storage[1]["final"] + storage[1]["saved"]
        return round(storage[1]["saved"] / original * 100, 1) if original > 0 else None

    @property
    def storage_saved_by_library(self) -> list[dict[str, Any]] | None:
        """Return storage savings per library."""
        storage = self._storage()
        return storage[0] if storage else None

    # NVIDIA

    @property
    def nvidia_info(self) -> dict[str, Any] | None:
        """Return NVIDIA SMI data."""
        return self._get("nvidia")


def enabled_count(items: list[dict[str, Any]] | None) -> int | None:
    """Return how many items are enabled."""
    return None if items is None else sum(1 for i in items if i.get("Enabled"))
