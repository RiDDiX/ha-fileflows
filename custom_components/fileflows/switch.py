"""Switch platform for FileFlows."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DEFAULT_PORT, DOMAIN
from .coordinator import FileFlowsDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up FileFlows switches."""
    coordinator: FileFlowsDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SwitchEntity] = []

    # System active switch (pause/resume)
    entities.append(FileFlowsSystemSwitch(coordinator, entry))

    # Per-node switches
    for node in coordinator.nodes:
        node_uid = node.get("Uid", "")
        node_name = node.get("Name", "Unknown")
        if node_uid:
            entities.append(
                FileFlowsNodeSwitch(coordinator, entry, node_uid, node_name)
            )

    # Per-library switches
    for library in coordinator.libraries:
        lib_uid = library.get("Uid", "")
        lib_name = library.get("Name", "Unknown")
        if lib_uid:
            entities.append(
                FileFlowsLibrarySwitch(coordinator, entry, lib_uid, lib_name)
            )

    # Per-flow switches
    for flow in coordinator.flows:
        flow_uid = flow.get("Uid", "")
        flow_name = flow.get("Name", "Unknown")
        if flow_uid:
            entities.append(
                FileFlowsFlowSwitch(coordinator, entry, flow_uid, flow_name)
            )

    async_add_entities(entities)


class FileFlowsSystemSwitch(
    CoordinatorEntity[FileFlowsDataUpdateCoordinator], SwitchEntity
):
    """Switch to pause/resume FileFlows processing."""

    _attr_has_entity_name = True
    _attr_name = "System Active"
    _attr_icon = "mdi:power"

    def __init__(
        self,
        coordinator: FileFlowsDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_system_active"
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
        """Return true if system is active (not paused)."""
        return not self.coordinator.is_paused

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Resume the system."""
        await self.coordinator.api.resume_system()
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Pause the system."""
        await self.coordinator.api.pause_system()
        await self.coordinator.async_request_refresh()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        return {
            "is_paused": self.coordinator.is_paused,
            "active_workers": self.coordinator.active_workers,
        }


class FileFlowsNodeSwitch(
    CoordinatorEntity[FileFlowsDataUpdateCoordinator], SwitchEntity
):
    """Switch to enable/disable a processing node."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: FileFlowsDataUpdateCoordinator,
        entry: ConfigEntry,
        node_uid: str,
        node_name: str,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._node_uid = node_uid
        self._node_name = node_name
        self._attr_unique_id = f"{entry.entry_id}_node_{node_uid}"
        self._attr_name = f"Node {node_name}"
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

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable the node."""
        await self.coordinator.api.enable_node(self._node_uid)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable the node."""
        await self.coordinator.api.disable_node(self._node_uid)
        await self.coordinator.async_request_refresh()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        for node in self.coordinator.nodes:
            if node.get("Uid") == self._node_uid:
                return {
                    "uid": self._node_uid,
                    "address": node.get("Address", "Unknown"),
                    "runners": node.get("FlowRunners", 0),
                    "priority": node.get("Priority", 0),
                }
        return {"uid": self._node_uid}


class FileFlowsLibrarySwitch(
    CoordinatorEntity[FileFlowsDataUpdateCoordinator], SwitchEntity
):
    """Switch to enable/disable a library."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: FileFlowsDataUpdateCoordinator,
        entry: ConfigEntry,
        lib_uid: str,
        lib_name: str,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._lib_uid = lib_uid
        self._lib_name = lib_name
        self._attr_unique_id = f"{entry.entry_id}_library_{lib_uid}"
        self._attr_name = f"Library {lib_name}"
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

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable the library."""
        await self.coordinator.api.enable_library(self._lib_uid)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable the library."""
        await self.coordinator.api.disable_library(self._lib_uid)
        await self.coordinator.async_request_refresh()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        for lib in self.coordinator.libraries:
            if lib.get("Uid") == self._lib_uid:
                return {
                    "uid": self._lib_uid,
                    "path": lib.get("Path", "Unknown"),
                    "priority": lib.get("Priority", 0),
                }
        return {"uid": self._lib_uid}


class FileFlowsFlowSwitch(
    CoordinatorEntity[FileFlowsDataUpdateCoordinator], SwitchEntity
):
    """Switch to enable/disable a flow."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: FileFlowsDataUpdateCoordinator,
        entry: ConfigEntry,
        flow_uid: str,
        flow_name: str,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._flow_uid = flow_uid
        self._flow_name = flow_name
        self._attr_unique_id = f"{entry.entry_id}_flow_{flow_uid}"
        self._attr_name = f"Flow {flow_name}"
        self._attr_icon = "mdi:sitemap"
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
        """Return true if the flow is enabled."""
        for flow in self.coordinator.flows:
            if flow.get("Uid") == self._flow_uid:
                return flow.get("Enabled", False)
        return False

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable the flow."""
        await self.coordinator.api.enable_flow(self._flow_uid)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable the flow."""
        await self.coordinator.api.disable_flow(self._flow_uid)
        await self.coordinator.async_request_refresh()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        for flow in self.coordinator.flows:
            if flow.get("Uid") == self._flow_uid:
                return {
                    "uid": self._flow_uid,
                    "type": flow.get("Type", "Unknown"),
                }
        return {"uid": self._flow_uid}
