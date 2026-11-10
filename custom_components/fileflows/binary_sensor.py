"""Binary sensor platform for FileFlows."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import FileFlowsConfigEntry, FileFlowsDataUpdateCoordinator
from .entity import FileFlowsEntity, add_item_entities


@dataclass(frozen=True, kw_only=True)
class FileFlowsBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describes FileFlows binary sensor entity."""

    value_fn: Callable[[FileFlowsDataUpdateCoordinator], bool | None]
    attr_fn: Callable[[FileFlowsDataUpdateCoordinator], dict[str, Any]] | None = None


def _positive(value: int | None) -> bool | None:
    return None if value is None else value > 0


def _all_nodes_enabled(c: FileFlowsDataUpdateCoordinator) -> bool | None:
    if c.nodes is None:
        return None
    return bool(c.nodes) and c.enabled_nodes_count == len(c.nodes)


BINARY_SENSOR_DESCRIPTIONS: tuple[FileFlowsBinarySensorEntityDescription, ...] = (
    FileFlowsBinarySensorEntityDescription(
        key="system_paused",
        translation_key="system_paused",
        icon="mdi:pause-circle",
        value_fn=lambda c: c.is_paused,
    ),
    FileFlowsBinarySensorEntityDescription(
        key="processing_active",
        translation_key="processing_active",
        icon="mdi:cog-sync",
        device_class=BinarySensorDeviceClass.RUNNING,
        value_fn=lambda c: c.is_processing,
        attr_fn=lambda c: {"workers": c.active_workers, "current_file": c.current_file},
    ),
    FileFlowsBinarySensorEntityDescription(
        key="has_failed_files",
        translation_key="has_failed_files",
        icon="mdi:alert-circle",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda c: _positive(c.files_failed),
        attr_fn=lambda c: {"failed_count": c.files_failed},
    ),
    FileFlowsBinarySensorEntityDescription(
        key="has_files_on_hold",
        translation_key="has_files_on_hold",
        icon="mdi:hand-back-left",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda c: _positive(c.files_on_hold),
        attr_fn=lambda c: {"on_hold_count": c.files_on_hold},
    ),
    FileFlowsBinarySensorEntityDescription(
        key="queue_not_empty",
        translation_key="queue_not_empty",
        icon="mdi:inbox-arrow-down",
        value_fn=lambda c: _positive(c.queue_size),
        attr_fn=lambda c: {
            "queue_size": c.queue_size,
            "unprocessed": c.files_unprocessed,
            "processing": c.files_processing,
        },
    ),
    FileFlowsBinarySensorEntityDescription(
        key="update_available",
        translation_key="update_available",
        icon="mdi:update",
        device_class=BinarySensorDeviceClass.UPDATE,
        value_fn=lambda c: c.update_available,
    ),
    FileFlowsBinarySensorEntityDescription(
        key="all_nodes_enabled",
        translation_key="all_nodes_enabled",
        icon="mdi:server-network",
        value_fn=_all_nodes_enabled,
        attr_fn=lambda c: {
            "enabled": c.enabled_nodes_count,
            "total": None if c.nodes is None else len(c.nodes),
        },
    ),
    FileFlowsBinarySensorEntityDescription(
        key="has_nvidia",
        translation_key="has_nvidia",
        icon="mdi:expansion-card-variant",
        value_fn=lambda c: None if c.nvidia_info is None else bool(c.nvidia_info),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FileFlowsConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up FileFlows binary sensors."""
    coordinator = entry.runtime_data
    async_add_entities(
        FileFlowsBinarySensor(coordinator, d) for d in BINARY_SENSOR_DESCRIPTIONS
    )
    add_item_entities(
        coordinator,
        entry,
        async_add_entities,
        "nodes",
        lambda uid, item: [
            FileFlowsItemBinarySensor(
                coordinator, "nodes", "node", uid, item, "mdi:server"
            )
        ],
    )
    add_item_entities(
        coordinator,
        entry,
        async_add_entities,
        "libraries",
        lambda uid, item: [
            FileFlowsItemBinarySensor(
                coordinator, "libraries", "library", uid, item, "mdi:folder"
            )
        ],
    )


class FileFlowsBinarySensor(FileFlowsEntity, BinarySensorEntity):
    """Representation of a FileFlows binary sensor."""

    entity_description: FileFlowsBinarySensorEntityDescription

    def __init__(
        self,
        coordinator: FileFlowsDataUpdateCoordinator,
        description: FileFlowsBinarySensorEntityDescription,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def available(self) -> bool:
        """Return False when the value source is absent."""
        return super().available and self.is_on is not None

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        return self.entity_description.value_fn(self.coordinator)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return additional state attributes."""
        if self.entity_description.attr_fn is None:
            return None
        return self.entity_description.attr_fn(self.coordinator)


class FileFlowsItemBinarySensor(FileFlowsEntity, BinarySensorEntity):
    """Whether a node or library is enabled."""

    def __init__(
        self,
        coordinator: FileFlowsDataUpdateCoordinator,
        kind: str,
        key: str,
        uid: str,
        item: dict[str, Any],
        icon: str,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, f"{key}_{uid}_enabled", kind, uid)
        self._attr_translation_key = f"{key}_enabled"
        self._attr_translation_placeholders = {"name": item.get("Name", "Unknown")}
        self._attr_icon = icon

    @property
    def is_on(self) -> bool | None:
        """Return true if the item is enabled."""
        return self.item.get("Enabled") if self.item else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        item = self.item or {}
        if self._kind == "nodes":
            return {
                "uid": self._uid,
                "address": item.get("Address"),
                "runners": item.get("FlowRunners"),
            }
        return {"uid": self._uid, "path": item.get("Path")}
