"""Sensor platform for FileFlows."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, PERCENTAGE, UnitOfInformation, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import FileFlowsDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class FileFlowsSensorEntityDescription(SensorEntityDescription):
    """Describes FileFlows sensor entity."""

    value_fn: Callable[[FileFlowsDataUpdateCoordinator], Any]
    attr_fn: Callable[[FileFlowsDataUpdateCoordinator], dict[str, Any]] | None = None


# =============================================================================
# Sensor Definitions
# =============================================================================
SENSOR_DESCRIPTIONS: tuple[FileFlowsSensorEntityDescription, ...] = (
    # -------------------------------------------------------------------------
    # Queue & Processing Sensors
    # -------------------------------------------------------------------------
    FileFlowsSensorEntityDescription(
        key="queue_size",
        translation_key="queue_size",
        name="Queue Size",
        icon="mdi:inbox-full",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="files",
        value_fn=lambda c: c.queue_size,
        attr_fn=lambda c: {
            "unprocessed": c.files_unprocessed,
            "processing": c.files_processing,
        },
    ),
    FileFlowsSensorEntityDescription(
        key="files_unprocessed",
        translation_key="files_unprocessed",
        name="Unprocessed Files",
        icon="mdi:file-clock-outline",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="files",
        value_fn=lambda c: c.files_unprocessed,
    ),
    FileFlowsSensorEntityDescription(
        key="files_processing",
        translation_key="files_processing",
        name="Processing Files",
        icon="mdi:file-sync-outline",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="files",
        value_fn=lambda c: c.files_processing,
        attr_fn=lambda c: {
            "processing_time": c.processing_time,
            "files": [
                {
                    "file": pf.get("name", pf.get("relativePath", "Unknown")),
                    "library": pf.get("library", "Unknown"),
                    "step": pf.get("step", "Unknown"),
                    "progress": pf.get("stepPercent", 0),
                }
                for pf in c.processing_files
            ] if c.processing_files else [],
        },
    ),
    FileFlowsSensorEntityDescription(
        key="files_processed",
        translation_key="files_processed",
        name="Processed Files",
        icon="mdi:file-check-outline",
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement="files",
        value_fn=lambda c: c.files_processed,
    ),
    FileFlowsSensorEntityDescription(
        key="files_failed",
        translation_key="files_failed",
        name="Failed Files",
        icon="mdi:file-alert-outline",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="files",
        value_fn=lambda c: c.files_failed,
    ),
    FileFlowsSensorEntityDescription(
        key="files_on_hold",
        translation_key="files_on_hold",
        name="Files On Hold",
        icon="mdi:file-clock",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="files",
        value_fn=lambda c: c.files_on_hold,
    ),
    FileFlowsSensorEntityDescription(
        key="files_out_of_schedule",
        translation_key="files_out_of_schedule",
        name="Files Out of Schedule",
        icon="mdi:file-cancel-outline",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="files",
        value_fn=lambda c: c.files_out_of_schedule,
    ),
    # -------------------------------------------------------------------------
    # Current Processing
    # -------------------------------------------------------------------------
    FileFlowsSensorEntityDescription(
        key="current_file",
        translation_key="current_file",
        name="Current File",
        icon="mdi:file-video-outline",
        value_fn=lambda c: c.current_file or "Idle",
        attr_fn=lambda c: {
            "workers_count": c.active_workers,
            "progress": c.current_file_progress,
            "step": c.current_step,
            "processing_time": c.processing_time,
            "details": [
                {
                    "file": pf.get("name", pf.get("relativePath", "Unknown")),
                    "library": pf.get("library", "Unknown"),
                    "step": pf.get("step", "Unknown"),
                    "progress": pf.get("stepPercent", 0),
                }
                for pf in c.processing_files
            ] if c.processing_files else [],
        },
    ),
    FileFlowsSensorEntityDescription(
        key="active_workers",
        translation_key="active_workers",
        name="Active Workers",
        icon="mdi:run-fast",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="workers",
        value_fn=lambda c: c.active_workers,
        attr_fn=lambda c: {
            "total_runners": c.total_runners,
        },
    ),
    FileFlowsSensorEntityDescription(
        key="processing_time",
        translation_key="processing_time",
        name="Processing Time",
        icon="mdi:timer-outline",
        value_fn=lambda c: c.processing_time or "00:00:00",
    ),
    # -------------------------------------------------------------------------
    # Storage Savings
    # -------------------------------------------------------------------------
    FileFlowsSensorEntityDescription(
        key="storage_saved",
        translation_key="storage_saved",
        name="Storage Saved",
        icon="mdi:harddisk",
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfInformation.GIGABYTES,
        suggested_display_precision=2,
        value_fn=lambda c: c.storage_saved_gb,
        attr_fn=lambda c: {
            "bytes_saved": c.storage_saved_bytes,
            "by_library": [
                {
                    "library": s.get("Library", "Unknown"),
                    "original_gb": round(s.get("OriginalSize", 0) / (1024**3), 2),
                    "final_gb": round(s.get("FinalSize", 0) / (1024**3), 2),
                    "saved_gb": round((s.get("OriginalSize", 0) - s.get("FinalSize", 0)) / (1024**3), 2),
                }
                for s in c.shrinkage_groups
            ],
        },
    ),
    FileFlowsSensorEntityDescription(
        key="storage_saved_percent",
        translation_key="storage_saved_percent",
        name="Storage Saved Percentage",
        icon="mdi:percent",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=1,
        value_fn=lambda c: c.storage_saved_percent,
    ),
    # -------------------------------------------------------------------------
    # System Resources
    # -------------------------------------------------------------------------
    FileFlowsSensorEntityDescription(
        key="cpu_usage",
        translation_key="cpu_usage",
        name="CPU Usage",
        icon="mdi:cpu-64-bit",
        device_class=SensorDeviceClass.POWER_FACTOR,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=1,
        value_fn=lambda c: c.cpu_usage,
    ),
    FileFlowsSensorEntityDescription(
        key="memory_usage",
        translation_key="memory_usage",
        name="Memory Usage",
        icon="mdi:memory",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=1,
        value_fn=lambda c: c.memory_usage,
        attr_fn=lambda c: {
            "used_mb": round(c.memory_used_mb, 0),
            "total_mb": round(c.memory_total_mb, 0),
        },
    ),
    FileFlowsSensorEntityDescription(
        key="temp_directory_size",
        translation_key="temp_directory_size",
        name="Temp Directory Size",
        icon="mdi:folder-clock",
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfInformation.GIGABYTES,
        suggested_display_precision=2,
        value_fn=lambda c: c.temp_directory_size_gb,
    ),
    FileFlowsSensorEntityDescription(
        key="log_directory_size",
        translation_key="log_directory_size",
        name="Log Directory Size",
        icon="mdi:folder-text",
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfInformation.GIGABYTES,
        suggested_display_precision=2,
        value_fn=lambda c: c.log_directory_size_gb,
    ),
    # -------------------------------------------------------------------------
    # Counts
    # -------------------------------------------------------------------------
    FileFlowsSensorEntityDescription(
        key="nodes_count",
        translation_key="nodes_count",
        name="Processing Nodes",
        icon="mdi:server-network",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="nodes",
        value_fn=lambda c: c.nodes_count,
        attr_fn=lambda c: {
            "enabled": c.enabled_nodes_count,
            "total_runners": c.total_runners,
            "nodes": [
                {
                    "name": n.get("Name", "Unknown"),
                    "enabled": n.get("Enabled", False),
                    "runners": n.get("FlowRunners", 0),
                    "address": n.get("Address", "Unknown"),
                }
                for n in c.nodes
            ],
        },
    ),
    FileFlowsSensorEntityDescription(
        key="libraries_count",
        translation_key="libraries_count",
        name="Libraries",
        icon="mdi:folder-multiple",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="libraries",
        value_fn=lambda c: c.libraries_count,
        attr_fn=lambda c: {
            "enabled": c.enabled_libraries_count,
            "libraries": [
                {
                    "name": lib.get("Name", "Unknown"),
                    "enabled": lib.get("Enabled", False),
                    "path": lib.get("Path", "Unknown"),
                }
                for lib in c.libraries
            ],
        },
    ),
    FileFlowsSensorEntityDescription(
        key="flows_count",
        translation_key="flows_count",
        name="Flows",
        icon="mdi:sitemap",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="flows",
        value_fn=lambda c: c.flows_count,
        attr_fn=lambda c: {
            "enabled": c.enabled_flows_count,
            "flows": [
                {
                    "name": f.get("Name", "Unknown"),
                    "enabled": f.get("Enabled", False),
                    "type": f.get("Type", "Unknown"),
                }
                for f in c.flows
            ],
        },
    ),
    FileFlowsSensorEntityDescription(
        key="plugins_count",
        translation_key="plugins_count",
        name="Plugins",
        icon="mdi:puzzle",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="plugins",
        value_fn=lambda c: c.plugins_count,
        attr_fn=lambda c: {
            "enabled": c.enabled_plugins_count,
            "plugins": [p.get("Name", "Unknown") for p in c.plugins[:20]],
        },
    ),
    FileFlowsSensorEntityDescription(
        key="tasks_count",
        translation_key="tasks_count",
        name="Scheduled Tasks",
        icon="mdi:calendar-clock",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="tasks",
        value_fn=lambda c: c.tasks_count,
        attr_fn=lambda c: {
            "tasks": [
                {
                    "name": t.get("Name", "Unknown"),
                    "type": t.get("Type", "Unknown"),
                }
                for t in c.tasks
            ],
        },
    ),
    # -------------------------------------------------------------------------
    # Version & Updates
    # -------------------------------------------------------------------------
    FileFlowsSensorEntityDescription(
        key="version",
        translation_key="version",
        name="Version",
        icon="mdi:tag-outline",
        value_fn=lambda c: c.version,
        attr_fn=lambda c: {
            "update_available": c.update_available,
        },
    ),
    # -------------------------------------------------------------------------
    # Recent Activity
    # -------------------------------------------------------------------------
    FileFlowsSensorEntityDescription(
        key="upcoming_count",
        translation_key="upcoming_count",
        name="Upcoming Files",
        icon="mdi:playlist-play",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="files",
        value_fn=lambda c: len(c.upcoming_files),
        attr_fn=lambda c: {
            "files": [
                {
                    "name": f.get("Name", f.get("RelativePath", "Unknown")),
                    "library": f.get("LibraryName", "Unknown"),
                }
                for f in c.upcoming_files[:10]
            ],
        },
    ),
    FileFlowsSensorEntityDescription(
        key="recently_finished_count",
        translation_key="recently_finished_count",
        name="Recently Finished",
        icon="mdi:playlist-check",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="files",
        value_fn=lambda c: len(c.recently_finished),
        attr_fn=lambda c: {
            "files": [
                {
                    "name": f.get("Name", f.get("RelativePath", "Unknown")),
                    "library": f.get("LibraryName", "Unknown"),
                }
                for f in c.recently_finished[:10]
            ],
        },
    ),
)

# =============================================================================
# NVIDIA Sensor Definitions (separate, only created if NVIDIA present)
# =============================================================================
NVIDIA_SENSOR_DESCRIPTIONS: tuple[FileFlowsSensorEntityDescription, ...] = (
    FileFlowsSensorEntityDescription(
        key="nvidia_gpu_usage",
        translation_key="nvidia_gpu_usage",
        name="NVIDIA GPU Usage",
        icon="mdi:expansion-card",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=1,
        value_fn=lambda c: c.nvidia_gpu_usage,
    ),
    FileFlowsSensorEntityDescription(
        key="nvidia_memory_usage",
        translation_key="nvidia_memory_usage",
        name="NVIDIA Memory Usage",
        icon="mdi:memory",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=1,
        value_fn=lambda c: c.nvidia_memory_usage,
    ),
    FileFlowsSensorEntityDescription(
        key="nvidia_encoder_usage",
        translation_key="nvidia_encoder_usage",
        name="NVIDIA Encoder Usage",
        icon="mdi:video-box",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=1,
        value_fn=lambda c: c.nvidia_encoder_usage,
    ),
    FileFlowsSensorEntityDescription(
        key="nvidia_decoder_usage",
        translation_key="nvidia_decoder_usage",
        name="NVIDIA Decoder Usage",
        icon="mdi:video-input-component",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=1,
        value_fn=lambda c: c.nvidia_decoder_usage,
    ),
    FileFlowsSensorEntityDescription(
        key="nvidia_temperature",
        translation_key="nvidia_temperature",
        name="NVIDIA Temperature",
        icon="mdi:thermometer",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=0,
        value_fn=lambda c: c.nvidia_temperature,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up FileFlows sensors."""
    coordinator: FileFlowsDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[FileFlowsSensor] = []

    # Add main sensors
    for description in SENSOR_DESCRIPTIONS:
        entities.append(FileFlowsSensor(coordinator, entry, description))

    # Add NVIDIA sensors if available
    if coordinator.has_nvidia:
        for description in NVIDIA_SENSOR_DESCRIPTIONS:
            entities.append(FileFlowsSensor(coordinator, entry, description))

    async_add_entities(entities)


class FileFlowsSensor(CoordinatorEntity[FileFlowsDataUpdateCoordinator], SensorEntity):
    """Representation of a FileFlows sensor."""

    entity_description: FileFlowsSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: FileFlowsDataUpdateCoordinator,
        entry: ConfigEntry,
        description: FileFlowsSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"FileFlows ({entry.data.get(CONF_HOST)})",
            manufacturer="FileFlows",
            model="Media Processing Server",
            sw_version=coordinator.version,
            configuration_url=f"http://{entry.data.get(CONF_HOST)}:{entry.data.get('port', 19200)}",
        )

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        try:
            return self.entity_description.value_fn(self.coordinator)
        except Exception as err:
            _LOGGER.debug("Error getting value for %s: %s", self.entity_description.key, err)
            return None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return additional state attributes."""
        if self.entity_description.attr_fn is None:
            return None
        try:
            return self.entity_description.attr_fn(self.coordinator)
        except Exception as err:
            _LOGGER.debug("Error getting attributes for %s: %s", self.entity_description.key, err)
            return None
