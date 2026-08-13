"""Sensor platform for NKSPAIR Integration."""
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import NKSPAIRConfigEntry

async def async_setup_entry(
    hass: HomeAssistant,
    entry: NKSPAIRConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up platform entries."""
    pass