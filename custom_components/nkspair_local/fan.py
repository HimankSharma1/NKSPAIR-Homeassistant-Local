"""Fan platform for NKSPAIR local integration."""
import logging
from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
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
    """Set up the fan platform dynamically."""
    coordinator = entry.runtime_data
    device_id = entry.data[CONF_DEVICE_ID]

    fans = []
    nodes = coordinator.config_payload.get("nodes", {})
    
    for node_id, node_data in nodes.items():
        if node_data.get("type") == "fan":
            _LOGGER.info("Adding fan entity for node: %s", node_id)
            fans.append(NKSPAIRFan(coordinator, device_id, node_id, node_data))

    if fans:
        async_add_entities(fans)


class NKSPAIRFan(CoordinatorEntity, FanEntity):
    """Representation of a dynamically created NKSPAIR Fan."""

    def __init__(
        self,
        coordinator: DeviceDataCoordinator,
        device_id: str,
        node_id: str,
        node_config: dict[str, Any],
    ) -> None:
        """Initialize the fan."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._node_id = node_id
        
        self._attr_unique_id = f"{device_id}_{node_id}"
        self._attr_name = node_id.capitalize()
        self._attr_has_entity_name = True
        
        # Base features
        self._attr_supported_features = FanEntityFeature.TURN_ON | FanEntityFeature.TURN_OFF
        
        # Check if speed control is supported
        properties = node_config.get("properties", {})
        if "speed" in properties:
            self._attr_supported_features |= FanEntityFeature.SET_SPEED

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
        """Return true if the fan is on."""
        data = self.coordinator.data or {}
        node_state = data.get(self._node_id, {})
        return node_state.get("power", False)

    @property
    def percentage(self) -> int | None:
        """Return the current speed percentage."""
        data = self.coordinator.data or {}
        node_state = data.get(self._node_id, {})
        return node_state.get("speed", 0)

    async def async_turn_on(self, percentage: int | None = None, preset_mode: str | None = None, **kwargs: Any) -> None:
        """Turn the fan on."""
        payload_data = {"power": True}
        
        if percentage is not None:
            payload_data["speed"] = percentage
            
        payload = {
            "action": "control",
            "payload": {
                self._node_id: payload_data
            }
        }
        await self.coordinator.async_send_command(payload)
        
        # Optimistically update state
        if self.coordinator.data is None:
            self.coordinator.data = {}
        if self._node_id not in self.coordinator.data:
            self.coordinator.data[self._node_id] = {}
        self.coordinator.data[self._node_id]["power"] = True
        if percentage is not None:
            self.coordinator.data[self._node_id]["speed"] = percentage
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the fan off."""
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

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the speed of the fan."""
        # If setting speed to > 0, we also usually want power=True
        power_state = True if percentage > 0 else False
        
        payload = {
            "action": "control",
            "payload": {
                self._node_id: {
                    "power": power_state,
                    "speed": percentage
                }
            }
        }
        await self.coordinator.async_send_command(payload)
        
        # Optimistically update state
        if self.coordinator.data is None:
            self.coordinator.data = {}
        if self._node_id not in self.coordinator.data:
            self.coordinator.data[self._node_id] = {}
        self.coordinator.data[self._node_id]["power"] = power_state
        self.coordinator.data[self._node_id]["speed"] = percentage
        self.async_write_ha_state()
