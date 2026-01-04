"""DataUpdateCoordinator for FileFlows."""
from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
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
        update_interval: timedelta = DEFAULT_SCAN_INTERVAL,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )
        self.api = api

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from API."""
        try:
            return await self.api.get_all_data()
        except FileFlowsApiError as err:
            raise UpdateFailed(f"Error communicating with FileFlows: {err}") from err

    # =========================================================================
    # Status Properties
    # =========================================================================
    @property
    def status(self) -> dict[str, Any]:
        """Get status data from /api/status."""
        return self.data.get("status", {}) if self.data else {}

    @property
    def is_paused(self) -> bool:
        """Check if system is paused."""
        # Check multiple sources for pause state
        status = self.fileflows_status
        if status:
            return status.get("IsPaused", False)
        return self.system_info.get("IsPaused", False)

    # =========================================================================
    # System Info Properties
    # =========================================================================
    @property
    def system_info(self) -> dict[str, Any]:
        """Get system info from /api/system/info."""
        return self.data.get("system_info", {}) if self.data else {}

    @property
    def fileflows_status(self) -> dict[str, Any]:
        """Get fileflows status from /api/settings/fileflows-status."""
        return self.data.get("fileflows_status", {}) if self.data else {}

    @property
    def version(self) -> str:
        """Get FileFlows version."""
        return self.data.get("version", "Unknown") if self.data else "Unknown"

    @property
    def update_available(self) -> bool:
        """Check if update is available."""
        return self.data.get("update_available", False) if self.data else False

    @property
    def cpu_usage(self) -> float:
        """Get CPU usage percentage."""
        return self.system_info.get("CpuUsage", 0.0)

    @property
    def memory_usage(self) -> float:
        """Get memory usage percentage."""
        return self.system_info.get("MemoryUsage", 0.0)

    @property
    def memory_used_mb(self) -> float:
        """Get memory used in MB."""
        return self.system_info.get("MemoryUsed", 0) / (1024 * 1024)

    @property
    def memory_total_mb(self) -> float:
        """Get total memory in MB."""
        return self.system_info.get("MemoryTotal", 0) / (1024 * 1024)

    @property
    def temp_directory_size_gb(self) -> float:
        """Get temp directory size in GB."""
        size = self.system_info.get("TempDirectorySize", 0)
        return round(size / (1024 ** 3), 2)

    @property
    def log_directory_size_gb(self) -> float:
        """Get log directory size in GB."""
        size = self.system_info.get("LogDirectorySize", 0)
        return round(size / (1024 ** 3), 2)

    # =========================================================================
    # Node Properties
    # =========================================================================
    @property
    def nodes(self) -> list[dict[str, Any]]:
        """Get all processing nodes."""
        return self.data.get("nodes", []) if self.data else []

    @property
    def nodes_count(self) -> int:
        """Get number of nodes."""
        return len(self.nodes)

    @property
    def enabled_nodes_count(self) -> int:
        """Get number of enabled nodes."""
        return len([n for n in self.nodes if n.get("Enabled", False)])

    @property
    def total_runners(self) -> int:
        """Get total number of runners from all enabled nodes."""
        return sum(n.get("FlowRunners", 0) for n in self.nodes if n.get("Enabled", False))

    # =========================================================================
    # Library Properties
    # =========================================================================
    @property
    def libraries(self) -> list[dict[str, Any]]:
        """Get all libraries."""
        return self.data.get("libraries", []) if self.data else []

    @property
    def libraries_count(self) -> int:
        """Get number of libraries."""
        return len(self.libraries)

    @property
    def enabled_libraries_count(self) -> int:
        """Get number of enabled libraries."""
        return len([lib for lib in self.libraries if lib.get("Enabled", False)])

    # =========================================================================
    # Flow Properties
    # =========================================================================
    @property
    def flows(self) -> list[dict[str, Any]]:
        """Get all flows."""
        return self.data.get("flows", []) if self.data else []

    @property
    def flows_count(self) -> int:
        """Get number of flows."""
        return len(self.flows)

    @property
    def enabled_flows_count(self) -> int:
        """Get number of enabled flows."""
        return len([f for f in self.flows if f.get("Enabled", False)])

    # =========================================================================
    # Worker Properties
    # =========================================================================
    @property
    def workers(self) -> list[dict[str, Any]]:
        """Get all running workers/executors."""
        return self.data.get("workers", []) if self.data else []

    @property
    def active_workers(self) -> int:
        """Get number of active workers."""
        return len(self.workers)

    @property
    def is_processing(self) -> bool:
        """Check if any files are being processed."""
        return len(self.workers) > 0

    @property
    def current_file(self) -> str | None:
        """Get current processing file name."""
        if self.workers:
            worker = self.workers[0]
            return worker.get("CurrentFile", worker.get("LibraryFile", {}).get("Name", "Unknown"))
        return None

    @property
    def current_file_progress(self) -> float:
        """Get current file progress percentage."""
        if self.workers:
            return self.workers[0].get("TotalParts", 0)
        return 0.0

    # =========================================================================
    # Library File Status Properties
    # =========================================================================
    @property
    def library_file_status(self) -> dict[str, Any]:
        """Get library file status overview."""
        return self.data.get("library_file_status", {}) if self.data else {}

    @property
    def files_unprocessed(self) -> int:
        """Get unprocessed files count."""
        return self.library_file_status.get("Unprocessed", 0)

    @property
    def files_processed(self) -> int:
        """Get processed files count."""
        return self.library_file_status.get("Processed", 0)

    @property
    def files_processing(self) -> int:
        """Get processing files count."""
        return self.library_file_status.get("Processing", 0)

    @property
    def files_failed(self) -> int:
        """Get failed files count."""
        return self.library_file_status.get("Failed", 0)

    @property
    def files_on_hold(self) -> int:
        """Get on hold files count."""
        return self.library_file_status.get("OnHold", 0)

    @property
    def files_out_of_schedule(self) -> int:
        """Get out of schedule files count."""
        return self.library_file_status.get("OutOfSchedule", 0)

    @property
    def files_disabled(self) -> int:
        """Get disabled files count."""
        return self.library_file_status.get("Disabled", 0)

    @property
    def queue_size(self) -> int:
        """Get total queue size (unprocessed + processing)."""
        return self.files_unprocessed + self.files_processing

    # =========================================================================
    # Upcoming & Recently Finished
    # =========================================================================
    @property
    def upcoming_files(self) -> list[dict[str, Any]]:
        """Get upcoming files to process."""
        return self.data.get("upcoming_files", []) if self.data else []

    @property
    def recently_finished(self) -> list[dict[str, Any]]:
        """Get recently finished files."""
        return self.data.get("recently_finished", []) if self.data else []

    # =========================================================================
    # Shrinkage Properties
    # =========================================================================
    @property
    def shrinkage_groups(self) -> list[dict[str, Any]]:
        """Get shrinkage data grouped by library."""
        return self.data.get("shrinkage_groups", []) if self.data else []

    @property
    def storage_saved_bytes(self) -> int:
        """Get total storage saved in bytes."""
        total = 0
        for item in self.shrinkage_groups:
            original = item.get("OriginalSize", 0)
            final = item.get("FinalSize", 0)
            if original > final:
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
        for item in self.shrinkage_groups:
            total_original += item.get("OriginalSize", 0)
            total_final += item.get("FinalSize", 0)

        if total_original > 0:
            return round(((total_original - total_final) / total_original) * 100, 1)
        return 0.0

    # =========================================================================
    # Task Properties
    # =========================================================================
    @property
    def tasks(self) -> list[dict[str, Any]]:
        """Get all scheduled tasks."""
        return self.data.get("tasks", []) if self.data else []

    @property
    def tasks_count(self) -> int:
        """Get number of scheduled tasks."""
        return len(self.tasks)

    # =========================================================================
    # Plugin Properties
    # =========================================================================
    @property
    def plugins(self) -> list[dict[str, Any]]:
        """Get all plugins."""
        return self.data.get("plugins", []) if self.data else []

    @property
    def plugins_count(self) -> int:
        """Get number of plugins."""
        return len(self.plugins)

    @property
    def enabled_plugins_count(self) -> int:
        """Get number of enabled plugins."""
        return len([p for p in self.plugins if p.get("Enabled", False)])

    # =========================================================================
    # NVIDIA Properties
    # =========================================================================
    @property
    def nvidia_info(self) -> dict[str, Any]:
        """Get NVIDIA SMI info."""
        return self.data.get("nvidia", {}) if self.data else {}

    @property
    def has_nvidia(self) -> bool:
        """Check if NVIDIA GPU is available."""
        return bool(self.nvidia_info)

    @property
    def nvidia_gpu_usage(self) -> float:
        """Get NVIDIA GPU usage percentage."""
        return self.nvidia_info.get("GpuUsage", 0.0)

    @property
    def nvidia_memory_usage(self) -> float:
        """Get NVIDIA memory usage percentage."""
        return self.nvidia_info.get("MemoryUsage", 0.0)

    @property
    def nvidia_encoder_usage(self) -> float:
        """Get NVIDIA encoder usage percentage."""
        return self.nvidia_info.get("EncoderUsage", 0.0)

    @property
    def nvidia_decoder_usage(self) -> float:
        """Get NVIDIA decoder usage percentage."""
        return self.nvidia_info.get("DecoderUsage", 0.0)

    @property
    def nvidia_temperature(self) -> float:
        """Get NVIDIA GPU temperature."""
        return self.nvidia_info.get("Temperature", 0.0)
