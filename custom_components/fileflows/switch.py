"""Switch platform for FileFlows."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import FileFlowsApi, FileFlowsApiError
from .const import DOMAIN
from .coordinator import FileFlowsDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up FileFlows switches."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: FileFlowsDataUpdateCoordinator = data["coordinator"]
    api: FileFlowsApi = data["api"]

    entities: list[SwitchEntity] = []

    # System pause switch
    entities.append(
        FileFlowsSystemSwitch(
            coordinator,
            api,
            SwitchEntityDescription(
                key="system_active",
                name="System Active",
                icon="mdi:play-pause",
            ),
            entry,
        )
    )

    # Node enable/disable switches
    if coordinator.nodes:
        for node in coordinator.nodes:
            node_uid = node.get("Uid", "")
            node_name = node.get("Name", "Unknown")
            entities.append(
                FileFlowsNodeSwitch(
                    coordinator,
                    api,
                    SwitchEntityDescription(
                        key=f"node_{node_uid}",
                        name=f"Node {node_name}",
                        icon="mdi:server",
                    ),
                    entry,
                    node_uid,
                    node_name,
                )
            )

    async_add_entities(entities)


class FileFlowsSystemSwitch(CoordinatorEntity[FileFlowsDataUpdateCoordinator], SwitchEntity):
    """Representation of a FileFlows system switch."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: FileFlowsDataUpdateCoordinator,
        api: FileFlowsApi,
        description: SwitchEntityDescription,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self.entity_description = description
        self._api = api
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
        """Return true if the system is active (not paused)."""
        return not self.coordinator.is_paused

    @property
    def icon(self) -> str:
        """Return the icon."""
        return "mdi:play-circle" if self.is_on else "mdi:pause-circle"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        return {
            "paused": self.coordinator.is_paused,
            "processing_active": self.coordinator.is_processing,
            "queue_size": self.coordinator.queue_size,
            "active_runners": self.coordinator.active_runners,
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the system (resume)."""
        try:
            await self._api.resume_system()
            _LOGGER.info("FileFlows system resumed")
        except FileFlowsApiError as err:
            _LOGGER.error("Failed to resume system: %s", err)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the system (pause)."""
        try:
            await self._api.pause_system()
            _LOGGER.info("FileFlows system paused")
        except FileFlowsApiError as err:
            _LOGGER.error("Failed to pause system: %s", err)
        await self.coordinator.async_request_refresh()


class FileFlowsNodeSwitch(CoordinatorEntity[FileFlowsDataUpdateCoordinator], SwitchEntity):
    """Representation of a FileFlows node switch."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: FileFlowsDataUpdateCoordinator,
        api: FileFlowsApi,
        description: SwitchEntityDescription,
        entry: ConfigEntry,
        node_uid: str,
        node_name: str,
    ) -> None:
        """Initialize the node switch."""
        super().__init__(coordinator)
        self.entity_description = description
        self._api = api
        self._node_uid = node_uid
        self._node_name = node_name
        self._attr_unique_id = f"{entry.entry_id}_node_switch_{node_uid}"
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
        """Return true if the node is enabled."""
        for node in self.coordinator.nodes:
            if node.get("Uid") == self._node_uid:
                return node.get("Enabled", False)
        return False

    @property
    def icon(self) -> str:
        """Return the icon."""
        return "mdi:server" if self.is_on else "mdi:server-off"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        for node in self.coordinator.nodes:
            if node.get("Uid") == self._node_uid:
                return {
                    "uid": node.get("Uid", ""),
                    "name": node.get("Name", "Unknown"),
                    "address": node.get("Address", ""),
                    "runners": node.get("FlowRunners", 0),
                    "version": node.get("Version", "Unknown"),
                    "operating_system": node.get("OperatingSystem", "Unknown"),
                    "architecture": node.get("Architecture", "Unknown"),
                }
        return {}

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable the node."""
        try:
            await self._api.enable_node(self._node_uid)
            _LOGGER.info("Node %s enabled", self._node_name)
        except FileFlowsApiError as err:
            _LOGGER.error("Failed to enable node %s: %s", self._node_name, err)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable the node."""
        try:
            await self._api.disable_node(self._node_uid)
            _LOGGER.info("Node %s disabled", self._node_name)
        except FileFlowsApiError as err:
            _LOGGER.error("Failed to disable node %s: %s", self._node_name, err)
        await self.coordinator.async_request_refresh()
