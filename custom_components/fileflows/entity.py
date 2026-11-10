"""Base entity for FileFlows."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from homeassistant.const import CONF_HOST
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import FileFlowsConfigEntry, FileFlowsDataUpdateCoordinator

MAX_LIST_ITEMS = 25


class FileFlowsEntity(CoordinatorEntity[FileFlowsDataUpdateCoordinator]):
    """FileFlows entity, optionally bound to one node, library, flow or task."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: FileFlowsDataUpdateCoordinator,
        unique_suffix: str,
        kind: str | None = None,
        uid: str | None = None,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        entry = coordinator.config_entry
        host = entry.data[CONF_HOST]
        self._kind = kind
        self._uid = uid
        self._attr_unique_id = f"{entry.entry_id}_{unique_suffix}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"FileFlows ({host})",
            manufacturer="FileFlows",
            model="Media Processing Server",
            sw_version=coordinator.version,
            configuration_url=coordinator.api.base_url,
        )

    @property
    def item(self) -> dict[str, Any] | None:
        """Return the bound item, if any."""
        if self._kind is None or self._uid is None:
            return None
        return self.coordinator.item(self._kind, self._uid)

    @property
    def available(self) -> bool:
        """Return False when the bound item is gone."""
        return super().available and (self._kind is None or self.item is not None)


def capped(items: list[Any]) -> list[Any]:
    """Keep attribute lists below the recorder size limit."""
    return items[:MAX_LIST_ITEMS]


def add_item_entities(
    coordinator: FileFlowsDataUpdateCoordinator,
    entry: FileFlowsConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
    kind: str,
    factory: Callable[[str, dict[str, Any]], Iterable[Entity]],
) -> None:
    """Add entities for items of one kind, including ones that appear later."""
    known: set[str] = set()

    @callback
    def _add_new() -> None:
        new = {
            uid: item
            for uid, item in coordinator.index(kind).items()
            if uid not in known
        }
        if not new:
            return
        known.update(new)
        async_add_entities(
            [entity for uid, item in new.items() for entity in factory(uid, item)]
        )

    _add_new()
    entry.async_on_unload(coordinator.async_add_listener(_add_new))
