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
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DEFAULT_PORT, DOMAIN
from .coordinator import FileFlowsDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class FileFlowsBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describes FileFlows binary sensor entity."""

    value_fn: Callable[[FileFlowsDataUpdateCoordinator], bool]
    attr_fn: Callable[[FileFlowsDataUpdateCoordinator], dict[str, Any]] | None = None


BINARY_SENSOR_DESCRIPTIONS: tuple[FileFlowsBinarySensorEntityDescription, ...] = (
    FileFlowsBinarySensorEntityDescription(
        key="system_paused",
        translation_key="system_paused",
        name="System Paused",
        icon="mdi:pause-circle",
        device_class=BinarySensorDeviceClass.RUNNING,
        value_fn=lambda c: not c.is_paused,  # Running = not paused
    ),
    FileFlowsBinarySensorEntityDescription(
        key="processing_active",
        translation_key="processing_active",
        name="Processing Active",
        icon="mdi:cog-sync",
        device_class=BinarySensorDeviceClass.RUNNING,
        value_fn=lambda c: c.is_processing,
        attr_fn=lambda c: {
            "workers": c.active_workers,
            "current_file": c.current_file,
        },
    ),
    FileFlowsBinarySensorEntityDescription(
        key="has_failed_files",
        translation_key="has_failed_files",
        name="Has Failed Files",
        icon="mdi:alert-circle",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda c: c.files_failed > 0,
        attr_fn=lambda c: {
            "failed_count": c.files_failed,
        },
    ),
    FileFlowsBinarySensorEntityDescription(
        key="has_files_on_hold",
        translation_key="has_files_on_hold",
        name="Has Files On Hold",
        icon="mdi:hand-back-left",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda c: c.files_on_hold > 0,
        attr_fn=lambda c: {
            "on_hold_count": c.files_on_hold,
        },
    ),
    FileFlowsBinarySensorEntityDescription(
        key="queue_not_empty",
        translation_key="queue_not_empty",
        name="Queue Not Empty",
        icon="mdi:inbox-arrow-down",
        value_fn=lambda c: c.queue_size > 0,
        attr_fn=lambda c: {
            "queue_size": c.queue_size,
            "unprocessed": c.files_unprocessed,
            "processing": c.files_processing,
        },
    ),
    FileFlowsBinarySensorEntityDescription(
        key="update_available",
        translation_key="update_available",
        name="Update Available",
        icon="mdi:update",
        device_class=BinarySensorDeviceClass.UPDATE,
        value_fn=lambda c: c.update_available,
    ),
    FileFlowsBinarySensorEntityDescription(
        key="all_nodes_enabled",
        translation_key="all_nodes_enabled",
        name="All Nodes Enabled",
        icon="mdi:server-network",
        value_fn=lambda c: c.nodes_count > 0 and c.enabled_nodes_count == c.nodes_count,
        attr_fn=lambda c: {
            "enabled": c.enabled_nodes_count,
            "total": c.nodes_count,
        },
    ),
    FileFlowsBinarySensorEntityDescription(
        key="has_nvidia",
        translation_key="has_nvidia",
        name="NVIDIA Available",
        icon="mdi:expansion-card-variant",
        value_fn=lambda c: c.has_nvidia,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up FileFlows binary sensors."""
    coordinator: FileFlowsDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        FileFlowsBinarySensor(coordinator, entry, description)
        for description in BINARY_SENSOR_DESCRIPTIONS
    ]

    # Add per-node binary sensors
    for node in coordinator.nodes:
        node_uid = node.get("Uid", "")
        node_name = node.get("Name", "Unknown")
        if node_uid:
            entities.append(
                FileFlowsNodeBinarySensor(coordinator, entry, node_uid, node_name)
            )

    # Add per-library binary sensors
    for library in coordinator.libraries:
        lib_uid = library.get("Uid", "")
        lib_name = library.get("Name", "Unknown")
        if lib_uid:
            entities.append(
                FileFlowsLibraryBinarySensor(coordinator, entry, lib_uid, lib_name)
            )

    async_add_entities(entities)


class FileFlowsBinarySensor(
    CoordinatorEntity[FileFlowsDataUpdateCoordinator], BinarySensorEntity
):
    """Representation of a FileFlows binary sensor."""

    entity_description: FileFlowsBinarySensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: FileFlowsDataUpdateCoordinator,
        entry: ConfigEntry,
        description: FileFlowsBinarySensorEntityDescription,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"FileFlows ({entry.data.get(CONF_HOST)})",
            manufacturer="FileFlows",
            model="Media Processing Server",
            sw_version=coordinator.version,
            configuration_url=f"http://{entry.data.get(CONF_HOST)}:{entry.data.get(CONF_PORT, DEFAULT_PORT)}",
        )

    @property
    def is_on(self) -> bool:
        """Return true if the binary sensor is on."""
        try:
            return self.entity_description.value_fn(self.coordinator)
        except Exception as err:
            _LOGGER.debug("Error getting value for %s: %s", self.entity_description.key, err)
            return False

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


class FileFlowsNodeBinarySensor(
    CoordinatorEntity[FileFlowsDataUpdateCoordinator], BinarySensorEntity
):
    """Representation of a FileFlows node enabled binary sensor."""

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.RUNNING

    def __init__(
        self,
        coordinator: FileFlowsDataUpdateCoordinator,
        entry: ConfigEntry,
        node_uid: str,
        node_name: str,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._node_uid = node_uid
        self._node_name = node_name
        self._attr_unique_id = f"{entry.entry_id}_node_{node_uid}_enabled"
        self._attr_name = f"Node {node_name} Enabled"
        self._attr_icon = "mdi:server"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"FileFlows ({entry.data.get(CONF_HOST)})",
            manufacturer="FileFlows",
            model="Media Processing Server",
            sw_version=coordinator.version,
            configuration_url=f"http://{entry.data.get(CONF_HOST)}:{entry.data.get(CONF_PORT, DEFAULT_PORT)}",
        )

    @property
    def is_on(self) -> bool:
        """Return true if the node is enabled."""
        for node in self.coordinator.nodes:
            if node.get("Uid") == self._node_uid:
                return node.get("Enabled", False)
        return False

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        for node in self.coordinator.nodes:
            if node.get("Uid") == self._node_uid:
                return {
                    "uid": self._node_uid,
                    "address": node.get("Address", "Unknown"),
                    "runners": node.get("FlowRunners", 0),
                }
        return {"uid": self._node_uid}


class FileFlowsLibraryBinarySensor(
    CoordinatorEntity[FileFlowsDataUpdateCoordinator], BinarySensorEntity
):
    """Representation of a FileFlows library enabled binary sensor."""

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.RUNNING

    def __init__(
        self,
        coordinator: FileFlowsDataUpdateCoordinator,
        entry: ConfigEntry,
        lib_uid: str,
        lib_name: str,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._lib_uid = lib_uid
        self._lib_name = lib_name
        self._attr_unique_id = f"{entry.entry_id}_library_{lib_uid}_enabled"
        self._attr_name = f"Library {lib_name} Enabled"
        self._attr_icon = "mdi:folder"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"FileFlows ({entry.data.get(CONF_HOST)})",
            manufacturer="FileFlows",
            model="Media Processing Server",
            sw_version=coordinator.version,
            configuration_url=f"http://{entry.data.get(CONF_HOST)}:{entry.data.get(CONF_PORT, DEFAULT_PORT)}",
        )

    @property
    def is_on(self) -> bool:
        """Return true if the library is enabled."""
        for lib in self.coordinator.libraries:
            if lib.get("Uid") == self._lib_uid:
                return lib.get("Enabled", False)
        return False

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        for lib in self.coordinator.libraries:
            if lib.get("Uid") == self._lib_uid:
                return {
                    "uid": self._lib_uid,
                    "path": lib.get("Path", "Unknown"),
                }
        return {"uid": self._lib_uid}
