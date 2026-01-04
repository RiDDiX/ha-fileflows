"""Binary sensor platform for FileFlows."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import FileFlowsDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class FileFlowsBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describes FileFlows binary sensor entity."""

    value_fn: Callable[[FileFlowsDataUpdateCoordinator], bool]
    attr_fn: Callable[[FileFlowsDataUpdateCoordinator], dict[str, Any]] | None = None
    icon_on: str | None = None
    icon_off: str | None = None


BINARY_SENSOR_DESCRIPTIONS: tuple[FileFlowsBinarySensorEntityDescription, ...] = (
    FileFlowsBinarySensorEntityDescription(
        key="system_paused",
        translation_key="system_paused",
        name="System Paused",
        icon_on="mdi:pause-circle",
        icon_off="mdi:play-circle",
        value_fn=lambda c: c.is_paused,
        attr_fn=lambda c: {
            "version": c.version,
            "queue_size": c.queue_size,
        },
    ),
    FileFlowsBinarySensorEntityDescription(
        key="processing_active",
        translation_key="processing_active",
        name="Processing Active",
        device_class=BinarySensorDeviceClass.RUNNING,
        icon_on="mdi:progress-clock",
        icon_off="mdi:progress-check",
        value_fn=lambda c: c.is_processing,
        attr_fn=lambda c: {
            "active_files": len(c.processing_files),
            "current_file": c.current_file_name,
            "active_runners": c.active_runners,
            "total_runners": c.total_runners,
        },
    ),
    FileFlowsBinarySensorEntityDescription(
        key="has_failed_files",
        translation_key="has_failed_files",
        name="Has Failed Files",
        device_class=BinarySensorDeviceClass.PROBLEM,
        icon_on="mdi:alert-circle",
        icon_off="mdi:check-circle",
        value_fn=lambda c: c.failed_count > 0,
        attr_fn=lambda c: {
            "failed_count": c.failed_count,
        },
    ),
    FileFlowsBinarySensorEntityDescription(
        key="queue_not_empty",
        translation_key="queue_not_empty",
        name="Queue Has Files",
        icon_on="mdi:inbox-full",
        icon_off="mdi:inbox-outline",
        value_fn=lambda c: c.queue_size > 0,
        attr_fn=lambda c: {
            "queue_size": c.queue_size,
            "processing": len(c.processing_files),
        },
    ),
    FileFlowsBinarySensorEntityDescription(
        key="all_nodes_enabled",
        translation_key="all_nodes_enabled",
        name="All Nodes Enabled",
        icon_on="mdi:server-network",
        icon_off="mdi:server-network-off",
        value_fn=lambda c: all(n.get("Enabled", False) for n in c.nodes) if c.nodes else False,
        attr_fn=lambda c: {
            "total_nodes": len(c.nodes),
            "enabled_nodes": len([n for n in c.nodes if n.get("Enabled", False)]),
            "disabled_nodes": [n.get("Name", "Unknown") for n in c.nodes if not n.get("Enabled", False)],
        },
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up FileFlows binary sensors."""
    coordinator: FileFlowsDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entities: list[FileFlowsBinarySensor] = []

    for description in BINARY_SENSOR_DESCRIPTIONS:
        entities.append(FileFlowsBinarySensor(coordinator, description, entry))

    # Add node-specific binary sensors
    if coordinator.nodes:
        for node in coordinator.nodes:
            node_uid = node.get("Uid", "")
            node_name = node.get("Name", "Unknown")
            entities.append(
                FileFlowsNodeBinarySensor(
                    coordinator,
                    FileFlowsBinarySensorEntityDescription(
                        key=f"node_{node_uid}_enabled",
                        name=f"Node {node_name} Enabled",
                        icon_on="mdi:server",
                        icon_off="mdi:server-off",
                        value_fn=lambda c, uid=node_uid: _is_node_enabled(c, uid),
                        attr_fn=lambda c, uid=node_uid: _get_node_attrs(c, uid),
                    ),
                    entry,
                    node_uid,
                    node_name,
                )
            )

    async_add_entities(entities)


def _is_node_enabled(coordinator: FileFlowsDataUpdateCoordinator, node_uid: str) -> bool:
    """Check if node is enabled."""
    for node in coordinator.nodes:
        if node.get("Uid") == node_uid:
            return node.get("Enabled", False)
    return False


def _get_node_attrs(coordinator: FileFlowsDataUpdateCoordinator, node_uid: str) -> dict[str, Any]:
    """Get node attributes."""
    for node in coordinator.nodes:
        if node.get("Uid") == node_uid:
            return {
                "uid": node.get("Uid", ""),
                "name": node.get("Name", "Unknown"),
                "address": node.get("Address", ""),
                "runners": node.get("FlowRunners", 0),
                "version": node.get("Version", "Unknown"),
            }
    return {}


class FileFlowsBinarySensor(CoordinatorEntity[FileFlowsDataUpdateCoordinator], BinarySensorEntity):
    """Representation of a FileFlows binary sensor."""

    entity_description: FileFlowsBinarySensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: FileFlowsDataUpdateCoordinator,
        description: FileFlowsBinarySensorEntityDescription,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the binary sensor."""
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
    def is_on(self) -> bool:
        """Return the state of the binary sensor."""
        return self.entity_description.value_fn(self.coordinator)

    @property
    def icon(self) -> str | None:
        """Return the icon."""
        if self.is_on and self.entity_description.icon_on:
            return self.entity_description.icon_on
        if not self.is_on and self.entity_description.icon_off:
            return self.entity_description.icon_off
        return self.entity_description.icon

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return the state attributes."""
        if self.entity_description.attr_fn:
            return self.entity_description.attr_fn(self.coordinator)
        return None


class FileFlowsNodeBinarySensor(FileFlowsBinarySensor):
    """Representation of a FileFlows node binary sensor."""

    def __init__(
        self,
        coordinator: FileFlowsDataUpdateCoordinator,
        description: FileFlowsBinarySensorEntityDescription,
        entry: ConfigEntry,
        node_uid: str,
        node_name: str,
    ) -> None:
        """Initialize the node binary sensor."""
        super().__init__(coordinator, description, entry)
        self._node_uid = node_uid
        self._node_name = node_name
        self._attr_unique_id = f"{entry.entry_id}_node_{node_uid}_enabled"
