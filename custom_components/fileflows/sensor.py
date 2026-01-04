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
from homeassistant.const import CONF_HOST, UnitOfInformation
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


SENSOR_DESCRIPTIONS: tuple[FileFlowsSensorEntityDescription, ...] = (
    FileFlowsSensorEntityDescription(
        key="queue",
        translation_key="queue",
        name="Queue Size",
        icon="mdi:inbox-full",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="files",
        value_fn=lambda c: c.queue_size,
    ),
    FileFlowsSensorEntityDescription(
        key="files_processing",
        translation_key="files_processing",
        name="Processing Files",
        icon="mdi:file-sync-outline",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="files",
        value_fn=lambda c: len(c.processing_files),
        attr_fn=lambda c: {
            "files": [f.get("name", f.get("relativePath", "Unknown")) for f in c.processing_files],
            "details": [
                {
                    "name": f.get("name", "Unknown"),
                    "step": f.get("step", "Unknown"),
                    "progress": f.get("stepPercent", 0),
                    "library": f.get("library", "Unknown"),
                }
                for f in c.processing_files
            ],
        },
    ),
    FileFlowsSensorEntityDescription(
        key="files_processed",
        translation_key="files_processed",
        name="Processed Files",
        icon="mdi:file-check-outline",
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement="files",
        value_fn=lambda c: c.processed_count,
    ),
    FileFlowsSensorEntityDescription(
        key="files_failed",
        translation_key="files_failed",
        name="Failed Files",
        icon="mdi:file-alert-outline",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="files",
        value_fn=lambda c: c.failed_count,
    ),
    FileFlowsSensorEntityDescription(
        key="storage_saved",
        translation_key="storage_saved",
        name="Storage Saved",
        icon="mdi:harddisk",
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement="GB",
        suggested_display_precision=2,
        value_fn=lambda c: c.storage_saved_gb,
        attr_fn=lambda c: {
            "bytes_saved": c.storage_saved_bytes,
            "shrinkage_groups": [
                {
                    "library": s.get("Library", "Unknown"),
                    "original_size": s.get("OriginalSize", 0),
                    "final_size": s.get("FinalSize", 0),
                }
                for s in c.shrinkage if s.get("Library") != "###TOTAL###"
            ],
        },
    ),
    FileFlowsSensorEntityDescription(
        key="storage_saved_percent",
        translation_key="storage_saved_percent",
        name="Storage Saved Percentage",
        icon="mdi:percent",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="%",
        suggested_display_precision=1,
        value_fn=lambda c: c.storage_saved_percent,
    ),
    FileFlowsSensorEntityDescription(
        key="current_file",
        translation_key="current_file",
        name="Current Processing File",
        icon="mdi:file-video-outline",
        value_fn=lambda c: c.current_file_name or "None",
        attr_fn=lambda c: {
            "step": c.processing_files[0].get("step", "Unknown") if c.processing_files else "None",
            "progress": c.processing_files[0].get("stepPercent", 0) if c.processing_files else 0,
            "library": c.processing_files[0].get("library", "Unknown") if c.processing_files else "None",
        },
    ),
    FileFlowsSensorEntityDescription(
        key="processing_time",
        translation_key="processing_time",
        name="Processing Time",
        icon="mdi:timer-outline",
        value_fn=lambda c: c.status.get("time", "N/A"),
    ),
    FileFlowsSensorEntityDescription(
        key="nodes_count",
        translation_key="nodes_count",
        name="Processing Nodes",
        icon="mdi:server-network",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="nodes",
        value_fn=lambda c: len(c.nodes),
        attr_fn=lambda c: {
            "nodes": [
                {
                    "name": n.get("Name", n.get("name", "Unknown")),
                    "enabled": n.get("Enabled", n.get("enabled", False)),
                }
                for n in c.nodes
            ],
        },
    ),
    FileFlowsSensorEntityDescription(
        key="libraries_count",
        translation_key="libraries_count",
        name="Libraries",
        icon="mdi:folder-multiple-outline",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="libraries",
        value_fn=lambda c: len(c.libraries),
        attr_fn=lambda c: {
            "libraries": [
                {
                    "name": lib.get("Name", lib.get("name", "Unknown")),
                    "path": lib.get("Path", lib.get("path", "Unknown")),
                }
                for lib in c.libraries
            ],
        },
    ),
    FileFlowsSensorEntityDescription(
        key="flows_count",
        translation_key="flows_count",
        name="Flows",
        icon="mdi:sitemap-outline",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="flows",
        value_fn=lambda c: len(c.flows),
        attr_fn=lambda c: {
            "flows": [f.get("Name", f.get("name", "Unknown")) for f in c.flows],
        },
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up FileFlows sensors."""
    coordinator: FileFlowsDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entities: list[FileFlowsSensor] = []

    for description in SENSOR_DESCRIPTIONS:
        entities.append(FileFlowsSensor(coordinator, description, entry))

    # Add node-specific sensors
    if coordinator.nodes:
        for node in coordinator.nodes:
            node_uid = node.get("Uid", "")
            node_name = node.get("Name", "Unknown")
            entities.append(
                FileFlowsNodeSensor(
                    coordinator,
                    FileFlowsSensorEntityDescription(
                        key=f"node_{node_uid}_status",
                        name=f"Node {node_name} Status",
                        icon="mdi:server",
                        value_fn=lambda c, uid=node_uid: _get_node_status(c, uid),
                        attr_fn=lambda c, uid=node_uid: _get_node_attrs(c, uid),
                    ),
                    entry,
                    node_uid,
                    node_name,
                )
            )

    async_add_entities(entities)


def _get_node_status(coordinator: FileFlowsDataUpdateCoordinator, node_uid: str) -> str:
    """Get node status."""
    for node in coordinator.nodes:
        if node.get("Uid") == node_uid:
            if not node.get("Enabled", False):
                return "Disabled"
            return "Enabled"
    return "Unknown"


def _get_node_attrs(coordinator: FileFlowsDataUpdateCoordinator, node_uid: str) -> dict[str, Any]:
    """Get node attributes."""
    for node in coordinator.nodes:
        if node.get("Uid") == node_uid:
            return {
                "uid": node.get("Uid", ""),
                "address": node.get("Address", ""),
                "enabled": node.get("Enabled", False),
                "runners": node.get("FlowRunners", 0),
                "priority": node.get("Priority", 0),
                "version": node.get("Version", "Unknown"),
                "operating_system": node.get("OperatingSystem", "Unknown"),
                "architecture": node.get("Architecture", "Unknown"),
            }
    return {}


class FileFlowsSensor(CoordinatorEntity[FileFlowsDataUpdateCoordinator], SensorEntity):
    """Representation of a FileFlows sensor."""

    entity_description: FileFlowsSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: FileFlowsDataUpdateCoordinator,
        description: FileFlowsSensorEntityDescription,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"FileFlows ({entry.data[CONF_HOST]})",
            manufacturer="FileFlows",
            model="Media Processing Server",
            sw_version=coordinator.version,
            configuration_url=f"http://{entry.data[CONF_HOST]}:{entry.data.get('port', 19200)}",
        )

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        return self.entity_description.value_fn(self.coordinator)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return the state attributes."""
        if self.entity_description.attr_fn:
            return self.entity_description.attr_fn(self.coordinator)
        return None


class FileFlowsNodeSensor(FileFlowsSensor):
    """Representation of a FileFlows node sensor."""

    def __init__(
        self,
        coordinator: FileFlowsDataUpdateCoordinator,
        description: FileFlowsSensorEntityDescription,
        entry: ConfigEntry,
        node_uid: str,
        node_name: str,
    ) -> None:
        """Initialize the node sensor."""
        super().__init__(coordinator, description, entry)
        self._node_uid = node_uid
        self._node_name = node_name
        self._attr_unique_id = f"{entry.entry_id}_node_{node_uid}"
