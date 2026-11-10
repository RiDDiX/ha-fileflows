"""Sensor platform for FileFlows."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, UnitOfInformation, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import (
    GIB,
    FileFlowsConfigEntry,
    FileFlowsDataUpdateCoordinator,
    enabled_count,
)
from .entity import FileFlowsEntity, capped


@dataclass(frozen=True, kw_only=True)
class FileFlowsSensorEntityDescription(SensorEntityDescription):
    """Describes FileFlows sensor entity."""

    value_fn: Callable[[FileFlowsDataUpdateCoordinator], Any]
    attr_fn: Callable[[FileFlowsDataUpdateCoordinator], dict[str, Any]] | None = None


def _length(items: list[Any] | None) -> int | None:
    return None if items is None else len(items)


def _processing_files(c: FileFlowsDataUpdateCoordinator) -> list[dict[str, Any]]:
    return [
        {
            "file": pf.get("name") or pf.get("relativePath"),
            "library": pf.get("library"),
            "step": pf.get("step"),
            "progress": pf.get("stepPercent"),
        }
        for pf in capped(c.processing_files or [])
    ]


def _workers(c: FileFlowsDataUpdateCoordinator) -> list[dict[str, Any]]:
    return [
        {
            "uid": w.get("Uid"),
            "file": w.get("DisplayName"),
            "agent": w.get("AgentName"),
        }
        for w in capped(c.workers or [])
    ]


def _current_file(c: FileFlowsDataUpdateCoordinator) -> str | None:
    # Fenrus has a count but no file name, so idle vs. busy cannot be shown
    if not c.api.has_api:
        return None
    if (name := c.current_file) is not None:
        return name
    return "Idle" if c.is_processing is False else None


def _file_list(files: list[dict[str, Any]] | None) -> dict[str, Any]:
    return {
        "files": [
            {
                "name": f.get("DisplayName"),
                "library": f.get("LibraryName"),
                "uid": f.get("Uid"),
            }
            for f in capped(files or [])
        ]
    }


SENSOR_DESCRIPTIONS: tuple[FileFlowsSensorEntityDescription, ...] = (
    FileFlowsSensorEntityDescription(
        key="queue_size",
        translation_key="queue_size",
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
        icon="mdi:file-clock-outline",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="files",
        value_fn=lambda c: c.files_unprocessed,
    ),
    FileFlowsSensorEntityDescription(
        key="files_processing",
        translation_key="files_processing",
        icon="mdi:file-sync-outline",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="files",
        value_fn=lambda c: c.files_processing,
        attr_fn=lambda c: {
            "processing_time": c.processing_time,
            "files": _processing_files(c),
            "files_count": len(c.processing_files or []),
        },
    ),
    FileFlowsSensorEntityDescription(
        key="files_processed",
        translation_key="files_processed",
        icon="mdi:file-check-outline",
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement="files",
        value_fn=lambda c: c.files_processed,
    ),
    FileFlowsSensorEntityDescription(
        key="files_failed",
        translation_key="files_failed",
        icon="mdi:file-alert-outline",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="files",
        value_fn=lambda c: c.files_failed,
    ),
    FileFlowsSensorEntityDescription(
        key="files_on_hold",
        translation_key="files_on_hold",
        icon="mdi:file-clock",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="files",
        value_fn=lambda c: c.files_on_hold,
    ),
    FileFlowsSensorEntityDescription(
        key="files_out_of_schedule",
        translation_key="files_out_of_schedule",
        icon="mdi:file-cancel-outline",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="files",
        value_fn=lambda c: c.files_out_of_schedule,
    ),
    FileFlowsSensorEntityDescription(
        key="current_file",
        translation_key="current_file",
        icon="mdi:file-video-outline",
        value_fn=_current_file,
        attr_fn=lambda c: {
            "workers_count": c.active_workers,
            "progress": c.current_file_progress,
            "step": c.current_step,
            "processing_time": c.processing_time,
            "details": _processing_files(c),
        },
    ),
    FileFlowsSensorEntityDescription(
        key="active_workers",
        translation_key="active_workers",
        icon="mdi:run-fast",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="workers",
        value_fn=lambda c: c.active_workers,
        attr_fn=lambda c: {"total_runners": c.total_runners, "workers": _workers(c)},
    ),
    FileFlowsSensorEntityDescription(
        key="processing_time",
        translation_key="processing_time",
        icon="mdi:timer-outline",
        value_fn=lambda c: c.processing_time,
    ),
    FileFlowsSensorEntityDescription(
        key="storage_saved",
        translation_key="storage_saved",
        icon="mdi:harddisk",
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfInformation.GIGABYTES,
        suggested_display_precision=2,
        value_fn=lambda c: c.storage_saved_gb,
        attr_fn=lambda c: {
            "bytes_saved": c.storage_saved_bytes,
            "by_library": [
                {
                    "library": lib["library"],
                    "items": lib["items"],
                    "saved_gb": round(lib["saved"] / GIB, 2),
                    "final_gb": round(lib["final"] / GIB, 2),
                }
                for lib in capped(c.storage_saved_by_library or [])
            ],
            "by_library_count": len(c.storage_saved_by_library or []),
        },
    ),
    FileFlowsSensorEntityDescription(
        key="storage_saved_percent",
        translation_key="storage_saved_percent",
        icon="mdi:percent",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=1,
        value_fn=lambda c: c.storage_saved_percent,
    ),
    FileFlowsSensorEntityDescription(
        key="nodes_count",
        translation_key="nodes_count",
        icon="mdi:server-network",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="nodes",
        value_fn=lambda c: _length(c.nodes),
        attr_fn=lambda c: {
            "enabled": c.enabled_nodes_count,
            "total_runners": c.total_runners,
            "nodes": [
                {
                    "name": n.get("Name"),
                    "enabled": n.get("Enabled"),
                    "runners": n.get("FlowRunners"),
                    "address": n.get("Address"),
                }
                for n in capped(c.nodes or [])
            ],
        },
    ),
    FileFlowsSensorEntityDescription(
        key="libraries_count",
        translation_key="libraries_count",
        icon="mdi:folder-multiple",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="libraries",
        value_fn=lambda c: _length(c.libraries),
        attr_fn=lambda c: {
            "enabled": enabled_count(c.libraries),
            "libraries": [
                {
                    "name": lib.get("Name"),
                    "enabled": lib.get("Enabled"),
                    "path": lib.get("Path"),
                }
                for lib in capped(c.libraries or [])
            ],
        },
    ),
    FileFlowsSensorEntityDescription(
        key="flows_count",
        translation_key="flows_count",
        icon="mdi:sitemap",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="flows",
        value_fn=lambda c: _length(c.flows),
        attr_fn=lambda c: {
            "enabled": enabled_count(c.flows),
            "flows": [
                {
                    "name": f.get("Name"),
                    "enabled": f.get("Enabled"),
                    "type": f.get("Type"),
                }
                for f in capped(c.flows or [])
            ],
        },
    ),
    FileFlowsSensorEntityDescription(
        key="plugins_count",
        translation_key="plugins_count",
        icon="mdi:puzzle",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="plugins",
        value_fn=lambda c: _length(c.plugins),
        attr_fn=lambda c: {
            "enabled": enabled_count(c.plugins),
            "plugins": [p.get("Name") for p in capped(c.plugins or [])],
        },
    ),
    FileFlowsSensorEntityDescription(
        key="tasks_count",
        translation_key="tasks_count",
        icon="mdi:calendar-clock",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="tasks",
        value_fn=lambda c: _length(c.tasks),
        attr_fn=lambda c: {
            "tasks": [
                {"name": t.get("Name"), "type": t.get("Type")}
                for t in capped(c.tasks or [])
            ],
        },
    ),
    FileFlowsSensorEntityDescription(
        key="version",
        translation_key="version",
        icon="mdi:tag-outline",
        value_fn=lambda c: c.version,
        attr_fn=lambda c: {"update_available": c.update_available},
    ),
    FileFlowsSensorEntityDescription(
        key="upcoming_count",
        translation_key="upcoming_count",
        icon="mdi:playlist-play",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="files",
        value_fn=lambda c: _length(c.upcoming_files),
        attr_fn=lambda c: _file_list(c.upcoming_files),
    ),
    FileFlowsSensorEntityDescription(
        key="recently_finished_count",
        translation_key="recently_finished_count",
        icon="mdi:playlist-check",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="files",
        value_fn=lambda c: _length(c.recently_finished),
        attr_fn=lambda c: _file_list(c.recently_finished),
    ),
)

NVIDIA_SENSOR_DESCRIPTIONS: tuple[FileFlowsSensorEntityDescription, ...] = (
    FileFlowsSensorEntityDescription(
        key="nvidia_gpu_usage",
        translation_key="nvidia_gpu_usage",
        icon="mdi:expansion-card",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=1,
        value_fn=lambda c: (c.nvidia_info or {}).get("GpuUsage"),
    ),
    FileFlowsSensorEntityDescription(
        key="nvidia_memory_usage",
        translation_key="nvidia_memory_usage",
        icon="mdi:memory",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=1,
        value_fn=lambda c: (c.nvidia_info or {}).get("MemoryUsage"),
    ),
    FileFlowsSensorEntityDescription(
        key="nvidia_encoder_usage",
        translation_key="nvidia_encoder_usage",
        icon="mdi:video-box",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=1,
        value_fn=lambda c: (c.nvidia_info or {}).get("EncoderUsage"),
    ),
    FileFlowsSensorEntityDescription(
        key="nvidia_decoder_usage",
        translation_key="nvidia_decoder_usage",
        icon="mdi:video-input-component",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=1,
        value_fn=lambda c: (c.nvidia_info or {}).get("DecoderUsage"),
    ),
    FileFlowsSensorEntityDescription(
        key="nvidia_temperature",
        translation_key="nvidia_temperature",
        icon="mdi:thermometer",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=0,
        value_fn=lambda c: (c.nvidia_info or {}).get("Temperature"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FileFlowsConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up FileFlows sensors."""
    coordinator = entry.runtime_data
    descriptions = SENSOR_DESCRIPTIONS
    if coordinator.nvidia_info:
        descriptions += NVIDIA_SENSOR_DESCRIPTIONS
    async_add_entities(FileFlowsSensor(coordinator, d) for d in descriptions)


class FileFlowsSensor(FileFlowsEntity, SensorEntity):
    """Representation of a FileFlows sensor."""

    entity_description: FileFlowsSensorEntityDescription
    _unrecorded_attributes = frozenset(
        {
            "files",
            "details",
            "progress",
            "step",
            "processing_time",
            "by_library",
            "nodes",
            "libraries",
            "flows",
            "plugins",
            "tasks",
            "workers",
        }
    )

    def __init__(
        self,
        coordinator: FileFlowsDataUpdateCoordinator,
        description: FileFlowsSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def available(self) -> bool:
        """Return False when the value source is absent."""
        return super().available and self.native_value is not None

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        return self.entity_description.value_fn(self.coordinator)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return additional state attributes."""
        if self.entity_description.attr_fn is None:
            return None
        return self.entity_description.attr_fn(self.coordinator)
