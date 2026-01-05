"""Button platform for FileFlows."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.button import ButtonEntity
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
    """Set up FileFlows buttons."""
    coordinator: FileFlowsDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[ButtonEntity] = [
        FileFlowsPauseButton(coordinator, entry),
        FileFlowsResumeButton(coordinator, entry),
        FileFlowsRestartButton(coordinator, entry),
        FileFlowsRescanAllButton(coordinator, entry),
        FileFlowsRefreshButton(coordinator, entry),
    ]

    # Per-library rescan buttons
    for library in coordinator.libraries:
        lib_uid = library.get("Uid", "")
        lib_name = library.get("Name", "Unknown")
        if lib_uid:
            entities.append(
                FileFlowsLibraryRescanButton(coordinator, entry, lib_uid, lib_name)
            )

    # Per-task run buttons
    for task in coordinator.tasks:
        task_uid = task.get("Uid", "")
        task_name = task.get("Name", "Unknown")
        if task_uid:
            entities.append(
                FileFlowsTaskRunButton(coordinator, entry, task_uid, task_name)
            )

    async_add_entities(entities)


class FileFlowsPauseButton(
    CoordinatorEntity[FileFlowsDataUpdateCoordinator], ButtonEntity
):
    """Button to pause FileFlows."""

    _attr_has_entity_name = True
    _attr_name = "Pause System"
    _attr_icon = "mdi:pause"

    def __init__(
        self,
        coordinator: FileFlowsDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_pause"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"FileFlows ({entry.data.get(CONF_HOST)})",
            manufacturer="FileFlows",
            model="Media Processing Server",
            sw_version=coordinator.version,
            configuration_url=f"http://{entry.data.get(CONF_HOST)}:{entry.data.get(CONF_PORT, DEFAULT_PORT)}",
        )

    async def async_press(self) -> None:
        """Handle the button press."""
        await self.coordinator.api.pause_system()
        await self.coordinator.async_request_refresh()


class FileFlowsResumeButton(
    CoordinatorEntity[FileFlowsDataUpdateCoordinator], ButtonEntity
):
    """Button to resume FileFlows."""

    _attr_has_entity_name = True
    _attr_name = "Resume System"
    _attr_icon = "mdi:play"

    def __init__(
        self,
        coordinator: FileFlowsDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_resume"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"FileFlows ({entry.data.get(CONF_HOST)})",
            manufacturer="FileFlows",
            model="Media Processing Server",
            sw_version=coordinator.version,
            configuration_url=f"http://{entry.data.get(CONF_HOST)}:{entry.data.get(CONF_PORT, DEFAULT_PORT)}",
        )

    async def async_press(self) -> None:
        """Handle the button press."""
        await self.coordinator.api.resume_system()
        await self.coordinator.async_request_refresh()


class FileFlowsRestartButton(
    CoordinatorEntity[FileFlowsDataUpdateCoordinator], ButtonEntity
):
    """Button to restart FileFlows server."""

    _attr_has_entity_name = True
    _attr_name = "Restart Server"
    _attr_icon = "mdi:restart"

    def __init__(
        self,
        coordinator: FileFlowsDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_restart"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"FileFlows ({entry.data.get(CONF_HOST)})",
            manufacturer="FileFlows",
            model="Media Processing Server",
            sw_version=coordinator.version,
            configuration_url=f"http://{entry.data.get(CONF_HOST)}:{entry.data.get(CONF_PORT, DEFAULT_PORT)}",
        )

    async def async_press(self) -> None:
        """Handle the button press."""
        await self.coordinator.api.restart_system()


class FileFlowsRescanAllButton(
    CoordinatorEntity[FileFlowsDataUpdateCoordinator], ButtonEntity
):
    """Button to rescan all libraries."""

    _attr_has_entity_name = True
    _attr_name = "Rescan All Libraries"
    _attr_icon = "mdi:folder-refresh"

    def __init__(
        self,
        coordinator: FileFlowsDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_rescan_all"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"FileFlows ({entry.data.get(CONF_HOST)})",
            manufacturer="FileFlows",
            model="Media Processing Server",
            sw_version=coordinator.version,
            configuration_url=f"http://{entry.data.get(CONF_HOST)}:{entry.data.get(CONF_PORT, DEFAULT_PORT)}",
        )

    async def async_press(self) -> None:
        """Handle the button press."""
        await self.coordinator.api.rescan_all_libraries()
        await self.coordinator.async_request_refresh()


class FileFlowsRefreshButton(
    CoordinatorEntity[FileFlowsDataUpdateCoordinator], ButtonEntity
):
    """Button to refresh data."""

    _attr_has_entity_name = True
    _attr_name = "Refresh Data"
    _attr_icon = "mdi:refresh"

    def __init__(
        self,
        coordinator: FileFlowsDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_refresh"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"FileFlows ({entry.data.get(CONF_HOST)})",
            manufacturer="FileFlows",
            model="Media Processing Server",
            sw_version=coordinator.version,
            configuration_url=f"http://{entry.data.get(CONF_HOST)}:{entry.data.get(CONF_PORT, DEFAULT_PORT)}",
        )

    async def async_press(self) -> None:
        """Handle the button press."""
        await self.coordinator.async_request_refresh()


class FileFlowsLibraryRescanButton(
    CoordinatorEntity[FileFlowsDataUpdateCoordinator], ButtonEntity
):
    """Button to rescan a specific library."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: FileFlowsDataUpdateCoordinator,
        entry: ConfigEntry,
        lib_uid: str,
        lib_name: str,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self._lib_uid = lib_uid
        self._lib_name = lib_name
        self._attr_unique_id = f"{entry.entry_id}_rescan_{lib_uid}"
        self._attr_name = f"Rescan {lib_name}"
        self._attr_icon = "mdi:folder-refresh-outline"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"FileFlows ({entry.data.get(CONF_HOST)})",
            manufacturer="FileFlows",
            model="Media Processing Server",
            sw_version=coordinator.version,
            configuration_url=f"http://{entry.data.get(CONF_HOST)}:{entry.data.get(CONF_PORT, DEFAULT_PORT)}",
        )

    async def async_press(self) -> None:
        """Handle the button press."""
        await self.coordinator.api.rescan_libraries([self._lib_uid])
        await self.coordinator.async_request_refresh()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        return {"uid": self._lib_uid, "library": self._lib_name}


class FileFlowsTaskRunButton(
    CoordinatorEntity[FileFlowsDataUpdateCoordinator], ButtonEntity
):
    """Button to run a scheduled task."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: FileFlowsDataUpdateCoordinator,
        entry: ConfigEntry,
        task_uid: str,
        task_name: str,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self._task_uid = task_uid
        self._task_name = task_name
        self._attr_unique_id = f"{entry.entry_id}_task_{task_uid}"
        self._attr_name = f"Run Task {task_name}"
        self._attr_icon = "mdi:play-circle"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"FileFlows ({entry.data.get(CONF_HOST)})",
            manufacturer="FileFlows",
            model="Media Processing Server",
            sw_version=coordinator.version,
            configuration_url=f"http://{entry.data.get(CONF_HOST)}:{entry.data.get(CONF_PORT, DEFAULT_PORT)}",
        )

    async def async_press(self) -> None:
        """Handle the button press."""
        await self.coordinator.api.run_task(self._task_uid)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        return {"uid": self._task_uid, "task": self._task_name}
