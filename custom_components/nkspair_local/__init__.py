"""The My Local Integration component."""
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN, CONF_HOST, CONF_PORT, CONF_MDNS_NAME, CONF_DEVICE_ID
from .coordinator import DeviceDataCoordinator

type NKSPAIRConfigEntry = ConfigEntry[DeviceDataCoordinator]

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: NKSPAIRConfigEntry) -> bool:
    """Set up My Local Integration from a config entry."""
    _LOGGER.info("Setting up device entry: %s", entry.title)

    host = entry.data[CONF_HOST]
    port = entry.data.get(CONF_PORT, 1884)
    mdns_name = entry.data.get(CONF_MDNS_NAME, entry.data.get(CONF_DEVICE_ID)) # Fallback if mdns_name is missing

    from homeassistant.exceptions import ConfigEntryNotReady

    # 1. Instantiate the coordinator
    coordinator = DeviceDataCoordinator(hass, host, port, mdns_name)

    # 2. Connect to MQTT and wait for configuration payload
    try:
        await coordinator.async_connect()
    except Exception as err:
        _LOGGER.warning("Device %s is offline or not responding. Will retry in background.", mdns_name)
        raise ConfigEntryNotReady(f"Failed to connect to device: {err}") from err

    # 3. Register the device in Home Assistant's Device Registry
    device_registry = dr.async_get(hass)
    device_info = coordinator.config_payload.get("device_info", {})
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.data[CONF_DEVICE_ID])},
        name=device_info.get("name", entry.title),
        manufacturer="NKSPAIR",
        model="NKSPAIR_SMARTLINK",
    )

    # 4. Store the coordinator object
    entry.runtime_data = coordinator

    # 5. Dynamically determine which platforms to load based on received nodes
    platforms = {Platform.BUTTON} # Always load the button platform for 'Identify'
    nodes = coordinator.config_payload.get("nodes", {})
    for node_id, node_data in nodes.items():
        node_type = node_data.get("type")
        if node_type == "switch":
            platforms.add(Platform.SWITCH)
        elif node_type == "fan":
            platforms.add(Platform.FAN)
            
    # Save the platforms we decided to load for unloading later
    coordinator.platforms = list(platforms)

    # 6. Forward setup to entity platforms
    if platforms:
        await hass.config_entries.async_forward_entry_setups(entry, list(platforms))

    # 7. Listen for changes to the config entry (e.g., mDNS IP updates)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True

async def async_reload_entry(hass: HomeAssistant, entry: NKSPAIRConfigEntry) -> None:
    """Reload config entry when data changes (like IP address)."""
    await hass.config_entries.async_reload(entry.entry_id)



async def async_unload_entry(hass: HomeAssistant, entry: NKSPAIRConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info("Unloading device entry: %s", entry.title)

    coordinator = entry.runtime_data
    if coordinator:
        await coordinator.async_shutdown()

    platforms = getattr(coordinator, "platforms", [])
    if platforms:
        unload_ok = await hass.config_entries.async_unload_platforms(entry, platforms)
    else:
        unload_ok = True

    return unload_ok