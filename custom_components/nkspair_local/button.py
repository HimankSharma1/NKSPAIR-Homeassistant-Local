"""Button platform for NKSPAIR Integration."""
import logging
from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import NKSPAIRConfigEntry
from .const import DOMAIN, CONF_DEVICE_ID

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: NKSPAIRConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the button platform."""
    coordinator = entry.runtime_data
    
    entities = []
    entities.append(IdentifyButton(coordinator, entry.data[CONF_DEVICE_ID]))
    
    async_add_entities(entities)


class IdentifyButton(CoordinatorEntity, ButtonEntity):
    """Button to identify the ESP32 device."""

    _attr_has_entity_name = True
    _attr_name = "Identify"
    _attr_icon = "mdi:magnify"

    def __init__(self, coordinator, device_id: str) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self.device_id = device_id
        
        # Make sure the unique ID is tied to the physical device
        self._attr_unique_id = f"{device_id}_identify"

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device registry information for this entity."""
        device_info = self.coordinator.config_payload.get("device_info", {})
        return {
            "identifiers": {(DOMAIN, self.device_id)},
            "name": device_info.get("name", "NKSPAIR Device"),
            "manufacturer": "NKSPAIR",
            "model": "NKSPAIR_SMARTLINK",
        }

    async def async_press(self) -> None:
        """Press the button to identify the device."""
        payload = {
            "action": "identify"
        }
        await self.coordinator.async_send_command(payload)
