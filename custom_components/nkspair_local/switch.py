"""Switch platform for NKSPAIR local integration."""
import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import NKSPAIRConfigEntry
from .const import DOMAIN, CONF_DEVICE_ID
from .coordinator import DeviceDataCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: NKSPAIRConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the switch platform dynamically."""
    coordinator = entry.runtime_data
    device_id = entry.data[CONF_DEVICE_ID]

    switches = []
    nodes = coordinator.config_payload.get("nodes", {})
    
    for node_id, node_data in nodes.items():
        if node_data.get("type") == "switch":
            _LOGGER.info("Adding switch entity for node: %s", node_id)
            switches.append(NKSPAIRSwitch(coordinator, device_id, node_id, node_data))

    if switches:
        async_add_entities(switches)


class NKSPAIRSwitch(CoordinatorEntity, SwitchEntity):
    """Representation of a dynamically created NKSPAIR Switch."""

    def __init__(
        self,
        coordinator: DeviceDataCoordinator,
        device_id: str,
        node_id: str,
        node_config: dict[str, Any],
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._node_id = node_id
        
        # Use node_id (e.g. switch1) as part of the unique ID
        self._attr_unique_id = f"{device_id}_{node_id}"
        # Set a friendly name
        self._attr_name = node_id.capitalize()
        self._attr_has_entity_name = True

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information about this entity."""
        device_info_payload = self.coordinator.config_payload.get("device_info", {})
        return {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": device_info_payload.get("name", "NKSPAIR Device"),
            "manufacturer": "NKSPAIR",
            "model": "NKSPAIR_SMARTLINK",
        }

    @property
    def is_on(self) -> bool | None:
        """Return true if the switch is on."""
        # Read the state payload: {"switch1": {"power": true}}
        data = self.coordinator.data or {}
        node_state = data.get(self._node_id, {})
        return node_state.get("power", False)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        payload = {
            "action": "control",
            "payload": {
                self._node_id: {
                    "power": True
                }
            }
        }
        await self.coordinator.async_send_command(payload)
        
        # Optimistically update state
        if self.coordinator.data is None:
            self.coordinator.data = {}
        if self._node_id not in self.coordinator.data:
            self.coordinator.data[self._node_id] = {}
        self.coordinator.data[self._node_id]["power"] = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        payload = {
            "action": "control",
            "payload": {
                self._node_id: {
                    "power": False
                }
            }
        }
        await self.coordinator.async_send_command(payload)
        
        # Optimistically update state
        if self.coordinator.data is None:
            self.coordinator.data = {}
        if self._node_id not in self.coordinator.data:
            self.coordinator.data[self._node_id] = {}
        self.coordinator.data[self._node_id]["power"] = False
        self.async_write_ha_state()