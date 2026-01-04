"""DataUpdateCoordinator for FileFlows."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import FileFlowsApi, FileFlowsApiError
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class FileFlowsDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching FileFlows data."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        api: FileFlowsApi,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the coordinator."""
        self.api = api
        self.config_entry = entry
        self._host = entry.data[CONF_HOST]
        self._port = entry.data[CONF_PORT]

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from FileFlows."""
        try:
            return await self.api.get_all_data()
        except FileFlowsApiError as err:
            raise UpdateFailed(f"Error communicating with FileFlows: {err}") from err

    @property
    def status(self) -> dict[str, Any]:
        """Get status data."""
        return self.data.get("status", {}) if self.data else {}

    @property
    def system_info(self) -> dict[str, Any]:
        """Get system info."""
        return self.data.get("system_info", {}) if self.data else {}

    @property
    def nodes(self) -> list[dict[str, Any]]:
        """Get nodes."""
        return self.data.get("nodes", []) if self.data else []

    @property
    def libraries(self) -> list[dict[str, Any]]:
        """Get libraries."""
        return self.data.get("libraries", []) if self.data else []

    @property
    def unprocessed_files(self) -> list[dict[str, Any]]:
        """Get unprocessed files."""
        return self.data.get("unprocessed_files", []) if self.data else []

    @property
    def processing_files(self) -> list[dict[str, Any]]:
        """Get processing files."""
        return self.data.get("processing_files", []) if self.data else []

    @property
    def processed_count(self) -> int:
        """Get processed files count."""
        return self.data.get("processed_count", 0) if self.data else 0

    @property
    def failed_count(self) -> int:
        """Get failed files count."""
        return self.data.get("failed_count", 0) if self.data else 0

    @property
    def statistics(self) -> dict[str, Any]:
        """Get statistics."""
        return self.data.get("statistics", {}) if self.data else {}

    @property
    def shrinkage(self) -> list[dict[str, Any]]:
        """Get shrinkage data."""
        return self.data.get("shrinkage", []) if self.data else []

    @property
    def workers(self) -> list[dict[str, Any]]:
        """Get workers."""
        return self.data.get("workers", []) if self.data else []

    @property
    def flows(self) -> list[dict[str, Any]]:
        """Get flows."""
        return self.data.get("flows", []) if self.data else []

    @property
    def is_paused(self) -> bool:
        """Check if system is paused."""
        return self.system_info.get("IsPaused", False)

    @property
    def is_processing(self) -> bool:
        """Check if any files are processing."""
        return len(self.processing_files) > 0

    @property
    def active_runners(self) -> int:
        """Get number of active runners."""
        return len([w for w in self.workers if w.get("Status") == "Processing"])

    @property
    def total_runners(self) -> int:
        """Get total number of runners."""
        return sum(n.get("FlowRunners", 0) for n in self.nodes if n.get("Enabled", False))

    @property
    def storage_saved_bytes(self) -> int:
        """Get total storage saved in bytes."""
        # Sum up all shrinkage groups
        total = 0
        for item in self.shrinkage:
            if item.get("Library") == "###TOTAL###":
                original = item.get("OriginalSize", 0)
                final = item.get("FinalSize", 0)
                return original - final
            original = item.get("OriginalSize", 0)
            final = item.get("FinalSize", 0)
            total += (original - final)
        return total

    @property
    def storage_saved_gb(self) -> float:
        """Get total storage saved in GB."""
        return round(self.storage_saved_bytes / (1024 ** 3), 2)

    @property
    def storage_saved_percent(self) -> float:
        """Get storage saved percentage."""
        total_original = 0
        total_final = 0
        for item in self.shrinkage:
            if item.get("Library") == "###TOTAL###":
                total_original = item.get("OriginalSize", 0)
                total_final = item.get("FinalSize", 0)
                break
            total_original += item.get("OriginalSize", 0)
            total_final += item.get("FinalSize", 0)
        
        if total_original > 0:
            return round(((total_original - total_final) / total_original) * 100, 1)
        return 0.0

    @property
    def current_file_name(self) -> str | None:
        """Get current processing file name."""
        if self.processing_files:
            file = self.processing_files[0]
            return file.get("name", file.get("relativePath", "Unknown"))
        return None

    @property
    def queue_size(self) -> int:
        """Get queue size from status."""
        return self.status.get("queue", len(self.unprocessed_files))

    @property
    def version(self) -> str:
        """Get FileFlows version."""
        return self.system_info.get("Version", "Unknown")

    @property
    def update_available(self) -> bool:
        """Check if update is available."""
        return self.data.get("update_available", False) if self.data else False
