"""Button platform for FileFlows."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api import FileFlowsApi
from .coordinator import FileFlowsConfigEntry, FileFlowsDataUpdateCoordinator
from .entity import FileFlowsEntity, add_item_entities


@dataclass(frozen=True, kw_only=True)
class FileFlowsButtonDescription(ButtonEntityDescription):
    """Describes a FileFlows button."""

    press_fn: Callable[[FileFlowsApi], Awaitable[None]] | None


@dataclass(frozen=True, kw_only=True)
class FileFlowsItemButtonDescription(ButtonEntityDescription):
    """Describes a button that acts on one library or task."""

    kind: str
    attr_name: str
    press_fn: Callable[[FileFlowsApi, str], Awaitable[None]]


BUTTONS: tuple[FileFlowsButtonDescription, ...] = (
    FileFlowsButtonDescription(
        key="pause",
        translation_key="pause",
        icon="mdi:pause",
        press_fn=lambda api: api.pause_system(),
    ),
    FileFlowsButtonDescription(
        key="resume",
        translation_key="resume",
        icon="mdi:play",
        press_fn=lambda api: api.resume_system(),
    ),
    FileFlowsButtonDescription(
        key="restart",
        translation_key="restart",
        icon="mdi:restart",
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        press_fn=lambda api: api.restart_system(),
    ),
    FileFlowsButtonDescription(
        key="rescan_all",
        translation_key="rescan_all",
        icon="mdi:folder-refresh",
        press_fn=lambda api: api.rescan_libraries(),
    ),
    FileFlowsButtonDescription(
        key="refresh",
        translation_key="refresh",
        icon="mdi:refresh",
        press_fn=None,
    ),
)

ITEM_BUTTONS: tuple[FileFlowsItemButtonDescription, ...] = (
    FileFlowsItemButtonDescription(
        key="rescan",
        translation_key="library_rescan",
        icon="mdi:folder-refresh-outline",
        kind="libraries",
        attr_name="library",
        press_fn=lambda api, uid: api.rescan_libraries([uid]),
    ),
    FileFlowsItemButtonDescription(
        key="task",
        translation_key="task_run",
        icon="mdi:play-circle",
        kind="tasks",
        attr_name="task",
        press_fn=lambda api, uid: api.run_task(uid),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FileFlowsConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up FileFlows buttons."""
    coordinator = entry.runtime_data
    if not coordinator.api.has_api:
        # every write needs the REST API; only the refresh button works without it
        async_add_entities(
            FileFlowsButton(coordinator, d) for d in BUTTONS if d.press_fn is None
        )
        return
    async_add_entities(FileFlowsButton(coordinator, d) for d in BUTTONS)
    for description in ITEM_BUTTONS:
        add_item_entities(
            coordinator,
            entry,
            async_add_entities,
            description.kind,
            lambda uid, item, d=description: [
                FileFlowsItemButton(coordinator, d, uid, item)
            ],
        )


class FileFlowsButton(FileFlowsEntity, ButtonEntity):
    """FileFlows system button."""

    entity_description: FileFlowsButtonDescription

    def __init__(
        self,
        coordinator: FileFlowsDataUpdateCoordinator,
        description: FileFlowsButtonDescription,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    async def async_press(self) -> None:
        """Handle the button press."""
        if self.entity_description.press_fn is None:
            await self.coordinator.async_request_refresh()
            return
        await self.coordinator.async_action(
            self.entity_description.press_fn(self.coordinator.api)
        )


class FileFlowsItemButton(FileFlowsEntity, ButtonEntity):
    """Button acting on one library or task."""

    entity_description: FileFlowsItemButtonDescription

    def __init__(
        self,
        coordinator: FileFlowsDataUpdateCoordinator,
        description: FileFlowsItemButtonDescription,
        uid: str,
        item: dict[str, Any],
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator, f"{description.key}_{uid}", description.kind, uid)
        self.entity_description = description
        self._name = item.get("Name", "Unknown")
        self._attr_translation_placeholders = {"name": self._name}

    async def async_press(self) -> None:
        """Handle the button press."""
        await self.coordinator.async_action(
            self.entity_description.press_fn(self.coordinator.api, self._uid)
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        return {"uid": self._uid, self.entity_description.attr_name: self._name}
