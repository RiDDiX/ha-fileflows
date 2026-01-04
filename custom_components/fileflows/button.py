"""Button platform for FileFlows."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
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


BUTTON_DESCRIPTIONS: tuple[ButtonEntityDescription, ...] = (
    ButtonEntityDescription(
        key="pause_system",
        name="Pause System",
        icon="mdi:pause-circle-outline",
    ),
    ButtonEntityDescription(
        key="resume_system",
        name="Resume System",
        icon="mdi:play-circle-outline",
    ),
    ButtonEntityDescription(
        key="refresh_data",
        name="Refresh Data",
        icon="mdi:refresh",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up FileFlows buttons."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: FileFlowsDataUpdateCoordinator = data["coordinator"]
    api: FileFlowsApi = data["api"]

    entities: list[ButtonEntity] = []

    for description in BUTTON_DESCRIPTIONS:
        entities.append(FileFlowsButton(coordinator, api, description, entry))

    # Add library rescan buttons
    if coordinator.libraries:
        for library in coordinator.libraries:
            lib_uid = library.get("Uid", "")
            lib_name = library.get("Name", "Unknown")
            entities.append(
                FileFlowsLibraryRescanButton(
                    coordinator,
                    api,
                    ButtonEntityDescription(
                        key=f"rescan_library_{lib_uid}",
                        name=f"Rescan {lib_name}",
                        icon="mdi:folder-sync-outline",
                    ),
                    entry,
                    lib_uid,
                    lib_name,
                )
            )

    async_add_entities(entities)


class FileFlowsButton(CoordinatorEntity[FileFlowsDataUpdateCoordinator], ButtonEntity):
    """Representation of a FileFlows button."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: FileFlowsDataUpdateCoordinator,
        api: FileFlowsApi,
        description: ButtonEntityDescription,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the button."""
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

    async def async_press(self) -> None:
        """Handle the button press."""
        try:
            if self.entity_description.key == "pause_system":
                await self._api.pause_system()
                _LOGGER.info("FileFlows system paused")
            elif self.entity_description.key == "resume_system":
                await self._api.resume_system()
                _LOGGER.info("FileFlows system resumed")
            elif self.entity_description.key == "refresh_data":
                await self.coordinator.async_request_refresh()
                _LOGGER.info("FileFlows data refreshed")
        except FileFlowsApiError as err:
            _LOGGER.error("Button action failed: %s", err)
        
        # Refresh data after action
        await self.coordinator.async_request_refresh()


class FileFlowsLibraryRescanButton(FileFlowsButton):
    """Representation of a FileFlows library rescan button."""

    def __init__(
        self,
        coordinator: FileFlowsDataUpdateCoordinator,
        api: FileFlowsApi,
        description: ButtonEntityDescription,
        entry: ConfigEntry,
        library_uid: str,
        library_name: str,
    ) -> None:
        """Initialize the library rescan button."""
        super().__init__(coordinator, api, description, entry)
        self._library_uid = library_uid
        self._library_name = library_name
        self._attr_unique_id = f"{entry.entry_id}_rescan_{library_uid}"

    async def async_press(self) -> None:
        """Handle the button press."""
        try:
            await self._api.rescan_library(self._library_uid)
            _LOGGER.info("Library %s rescan started", self._library_name)
        except FileFlowsApiError as err:
            _LOGGER.error("Library rescan failed: %s", err)
        
        # Refresh data after action
        await self.coordinator.async_request_refresh()
