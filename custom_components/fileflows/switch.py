"""Switch platform for FileFlows."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api import FileFlowsApi
from .coordinator import FileFlowsConfigEntry, FileFlowsDataUpdateCoordinator
from .entity import FileFlowsEntity, add_item_entities


@dataclass(frozen=True, kw_only=True)
class FileFlowsItemSwitchDescription(SwitchEntityDescription):
    """Describes a switch that enables or disables a node, library or flow."""

    kind: str
    set_fn: Callable[[FileFlowsApi, str, bool], Awaitable[None]]
    attr_fn: Callable[[dict[str, Any]], dict[str, Any]]


ITEM_SWITCHES: tuple[FileFlowsItemSwitchDescription, ...] = (
    FileFlowsItemSwitchDescription(
        key="node",
        translation_key="node",
        icon="mdi:server",
        kind="nodes",
        set_fn=lambda api, uid, on: api.set_node_state(uid, on),
        attr_fn=lambda item: {
            "address": item.get("Address"),
            "runners": item.get("FlowRunners"),
            "priority": item.get("Priority"),
        },
    ),
    FileFlowsItemSwitchDescription(
        key="library",
        translation_key="library",
        icon="mdi:folder",
        kind="libraries",
        set_fn=lambda api, uid, on: api.set_library_state(uid, on),
        attr_fn=lambda item: {
            "path": item.get("Path"),
            "priority": item.get("Priority"),
        },
    ),
    FileFlowsItemSwitchDescription(
        key="flow",
        translation_key="flow",
        icon="mdi:sitemap",
        kind="flows",
        set_fn=lambda api, uid, on: api.set_flow_state(uid, on),
        attr_fn=lambda item: {"type": item.get("Type")},
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FileFlowsConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up FileFlows switches."""
    coordinator = entry.runtime_data
    if not coordinator.api.has_api:
        return
    async_add_entities([FileFlowsSystemSwitch(coordinator)])
    for description in ITEM_SWITCHES:
        add_item_entities(
            coordinator,
            entry,
            async_add_entities,
            description.kind,
            lambda uid, item, d=description: [
                FileFlowsItemSwitch(coordinator, d, uid, item)
            ],
        )


class FileFlowsSystemSwitch(FileFlowsEntity, SwitchEntity):
    """Switch to pause/resume FileFlows processing."""

    _attr_translation_key = "system_active"
    _attr_icon = "mdi:power"

    def __init__(self, coordinator: FileFlowsDataUpdateCoordinator) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, "system_active")

    @property
    def available(self) -> bool:
        """Return False when the pause state is unknown."""
        return super().available and self.coordinator.is_paused is not None

    @property
    def is_on(self) -> bool | None:
        """Return true if the system is active (not paused)."""
        paused = self.coordinator.is_paused
        return None if paused is None else not paused

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Resume the system."""
        await self.coordinator.async_action(self.coordinator.api.resume_system())

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Pause the system."""
        await self.coordinator.async_action(self.coordinator.api.pause_system())

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        return {
            "is_paused": self.coordinator.is_paused,
            "active_workers": self.coordinator.active_workers,
        }


class FileFlowsItemSwitch(FileFlowsEntity, SwitchEntity):
    """Switch to enable or disable a node, library or flow."""

    entity_description: FileFlowsItemSwitchDescription

    def __init__(
        self,
        coordinator: FileFlowsDataUpdateCoordinator,
        description: FileFlowsItemSwitchDescription,
        uid: str,
        item: dict[str, Any],
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, f"{description.key}_{uid}", description.kind, uid)
        self.entity_description = description
        self._attr_translation_placeholders = {"name": item.get("Name", "Unknown")}

    @property
    def is_on(self) -> bool | None:
        """Return true if the item is enabled."""
        return self.item.get("Enabled") if self.item else None

    async def _set(self, enabled: bool) -> None:
        await self.coordinator.async_action(
            self.entity_description.set_fn(self.coordinator.api, self._uid, enabled)
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable the item."""
        await self._set(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable the item."""
        await self._set(False)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        return {"uid": self._uid, **self.entity_description.attr_fn(self.item or {})}
