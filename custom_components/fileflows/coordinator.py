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
    # Status Properties (from PUBLIC /remote/info/status endpoint)
    # =========================================================================
    @property
    def remote_status(self) -> dict[str, Any]:
        """Get status data from /remote/info/status (public endpoint).
        
        Returns: {queue, processing, processed, time, processingFiles[]}
        """
        return self.data.get("remote_status", {}) if self.data else {}

    @property
    def is_paused(self) -> bool:
        """Check if system is paused.

        Note: This information is not available in /remote/info/* endpoints.
        Returns False by default. Use the System Active switch to control pause state.
        """
        # Pause status not available in public endpoints
        # This will be managed by the switch entity
        return False

    @property
    def queue_from_remote(self) -> int:
        """Get queue size from remote status."""
        return self.remote_status.get("queue", 0)

    @property
    def processing_from_remote(self) -> int:
        """Get processing count from remote status."""
        return self.remote_status.get("processing", 0)

    @property
    def processed_from_remote(self) -> int:
        """Get processed count from remote status."""
        return self.remote_status.get("processed", 0)

    @property
    def processing_time(self) -> str:
        """Get processing time from remote status."""
        return self.remote_status.get("time", "")

    @property
    def processing_files(self) -> list[dict[str, Any]]:
        """Get currently processing files from remote status.
        
        Returns: [{name, relativePath, library, step, stepPercent}, ...]
        """
        return self.remote_status.get("processingFiles", [])

    # =========================================================================
    # System Info Properties - Now derived from remote_status
    # =========================================================================

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
        """Get CPU usage percentage.

        Note: Not available in /remote/info/* endpoints.
        """
        return 0.0

    @property
    def memory_usage(self) -> float:
        """Get memory usage percentage.

        Note: Not available in /remote/info/* endpoints.
        """
        return 0.0

    @property
    def memory_used_mb(self) -> float:
        """Get memory used in MB.

        Note: Not available in /remote/info/* endpoints.
        """
        return 0.0

    @property
    def memory_total_mb(self) -> float:
        """Get total memory in MB.

        Note: Not available in /remote/info/* endpoints.
        """
        return 0.0

    @property
    def temp_directory_size_gb(self) -> float:
        """Get temp directory size in GB.

        Note: Not available in /remote/info/* endpoints.
        """
        return 0.0

    @property
    def log_directory_size_gb(self) -> float:
        """Get log directory size in GB.

        Note: Not available in /remote/info/* endpoints.
        """
        return 0.0

    # =========================================================================
    # Node, Library, Flow Properties - Not available in /remote/info/* endpoints
    # These return 0 or empty lists since the data is not accessible
    # =========================================================================
    @property
    def nodes_count(self) -> int:
        """Get number of nodes. Not available in public endpoints."""
        return 0

    @property
    def enabled_nodes_count(self) -> int:
        """Get number of enabled nodes. Not available in public endpoints."""
        return 0

    @property
    def total_runners(self) -> int:
        """Get total number of runners. Not available in public endpoints."""
        return 0

    @property
    def libraries_count(self) -> int:
        """Get number of libraries. Not available in public endpoints."""
        return 0

    @property
    def enabled_libraries_count(self) -> int:
        """Get number of enabled libraries. Not available in public endpoints."""
        return 0

    @property
    def flows_count(self) -> int:
        """Get number of flows. Not available in public endpoints."""
        return 0

    @property
    def enabled_flows_count(self) -> int:
        """Get number of enabled flows. Not available in public endpoints."""
        return 0

    # =========================================================================
    # Worker Properties - Use remote_status processing_files
    # =========================================================================
    @property
    def active_workers(self) -> int:
        """Get number of active workers from processing files."""
        # Use processing_files from public remote_status endpoint
        pf = self.processing_files
        if pf:
            return len(pf)
        # Alternative: use processing count from remote_status
        return self.processing_from_remote

    @property
    def is_processing(self) -> bool:
        """Check if any files are being processed."""
        # Use remote_status (public endpoint)
        if self.processing_files:
            return True
        if self.processing_from_remote > 0:
            return True
        return False

    @property
    def current_file(self) -> str | None:
        """Get current processing file name."""
        # Use processingFiles from remote_status
        pf = self.processing_files
        if pf:
            return pf[0].get("name", pf[0].get("relativePath", "Unknown"))
        return None

    @property
    def current_file_progress(self) -> float:
        """Get current file progress percentage."""
        # Use processingFiles from remote_status
        pf = self.processing_files
        if pf:
            return pf[0].get("stepPercent", 0.0)
        return 0.0

    @property
    def current_step(self) -> str | None:
        """Get current processing step name."""
        pf = self.processing_files
        if pf:
            return pf[0].get("step", None)
        return None

    # =========================================================================
    # Library File Status Properties - From remote_status only
    # =========================================================================
    @property
    def files_unprocessed(self) -> int:
        """Get unprocessed files count from remote_status."""
        return self.queue_from_remote

    @property
    def files_processed(self) -> int:
        """Get processed files count from remote_status."""
        return self.processed_from_remote

    @property
    def files_processing(self) -> int:
        """Get processing files count from remote_status."""
        # Use processing count from remote_status
        processing = self.processing_from_remote
        if processing > 0:
            return processing
        # Or count processingFiles
        pf = self.processing_files
        if pf:
            return len(pf)
        return 0

    @property
    def files_failed(self) -> int:
        """Get failed files count. Not available in public endpoints."""
        return 0

    @property
    def files_on_hold(self) -> int:
        """Get on hold files count. Not available in public endpoints."""
        return 0

    @property
    def files_out_of_schedule(self) -> int:
        """Get out of schedule files count. Not available in public endpoints."""
        return 0

    @property
    def files_disabled(self) -> int:
        """Get disabled files count. Not available in public endpoints."""
        return 0

    @property
    def queue_size(self) -> int:
        """Get total queue size from remote_status."""
        return self.queue_from_remote

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
    # Task, Plugin, and NVIDIA Properties - Not available in /remote/info/*
    # =========================================================================
    @property
    def tasks_count(self) -> int:
        """Get number of scheduled tasks. Not available in public endpoints."""
        return 0

    @property
    def plugins_count(self) -> int:
        """Get number of plugins. Not available in public endpoints."""
        return 0

    @property
    def enabled_plugins_count(self) -> int:
        """Get number of enabled plugins. Not available in public endpoints."""
        return 0

    @property
    def has_nvidia(self) -> bool:
        """Check if NVIDIA GPU is available. Not available in public endpoints."""
        return False

    @property
    def nvidia_gpu_usage(self) -> float:
        """Get NVIDIA GPU usage percentage. Not available in public endpoints."""
        return 0.0

    @property
    def nvidia_memory_usage(self) -> float:
        """Get NVIDIA memory usage percentage. Not available in public endpoints."""
        return 0.0

    @property
    def nvidia_encoder_usage(self) -> float:
        """Get NVIDIA encoder usage percentage. Not available in public endpoints."""
        return 0.0

    @property
    def nvidia_decoder_usage(self) -> float:
        """Get NVIDIA decoder usage percentage. Not available in public endpoints."""
        return 0.0

    @property
    def nvidia_temperature(self) -> float:
        """Get NVIDIA GPU temperature. Not available in public endpoints."""
        return 0.0
