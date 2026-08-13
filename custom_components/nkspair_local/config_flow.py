"""Config flow for NKSPAIR Local Integration."""
import asyncio
from typing import Any
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.components import zeroconf as ha_zeroconf
from zeroconf import ServiceStateChange
from zeroconf.asyncio import AsyncServiceInfo, AsyncServiceBrowser

from .const import (
    DOMAIN,
    CONF_HOST,
    CONF_PORT,
    CONF_MAC,
    CONF_DEVICE_ID,
    CONF_NAME,
)

class ActiveMdnsScanner:
    """A helper to actively scan the network for a specific device ID in real-time."""
    
    def __init__(self, target_id: str) -> None:
        self.target_id = target_id
        self.found_info: dict[str, Any] | None = None
        self.event = asyncio.Event()

    def update_service(self, zeroconf, service_type, name, state_change, **kwargs) -> None:
        """Handle service state changes from zeroconf."""
        if state_change == ServiceStateChange.Added:
            # We must run the resolution in a background task to avoid blocking
            asyncio.create_task(self._async_resolve(zeroconf, service_type, name))

    async def _async_resolve(self, zeroconf, service_type, name) -> None:
        """Resolve the newly discovered service to get its TXT properties."""
        info = AsyncServiceInfo(service_type, name)
        await info.async_request(zeroconf, 3000)
        
        if info and info.properties:
            # Safely decode byte properties to standard strings
            props = {}
            for k, v in info.properties.items():
                key = k.decode("utf-8") if isinstance(k, bytes) else k
                val = v.decode("utf-8") if isinstance(v, bytes) else v
                props[key] = val
                
            if props.get("id") == self.target_id:
                # Target found! Extract the relevant data
                addresses = info.parsed_addresses()
                self.found_info = {
                    CONF_HOST: addresses[0] if addresses else None,
                    CONF_PORT: info.port or 1884,
                    CONF_NAME: props.get("name", "Smartlink Device"),
                    CONF_DEVICE_ID: props.get("id", ""),
                    CONF_MAC: props.get("mac", ""),
                    "mf": props.get("mf", ""),
                    "model": props.get("model", ""),
                    "mdns_name": name.split('.')[0],
                }
                self.event.set()


class MyLocalIntegrationConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for My Local Integration."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self.discovery_info: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the manual setup step where the user enters the Device ID."""
        errors = {}

        if user_input is not None:
            device_id = user_input[CONF_DEVICE_ID].strip()

            # 1. Check Home Assistant's database to see if it is already paired
            for entry in self._async_current_entries():
                if entry.data.get(CONF_DEVICE_ID) == device_id:
                    return self.async_abort(reason="already_configured")

            # 2. Perform a fresh, real-time mDNS scan (NO CACHE)
            errors = await self._async_perform_fresh_scan(device_id)
            
            if not errors:
                # If no errors were returned, the device is online and valid
                return await self.async_step_zeroconf_confirm()

        # Show the manual entry form (or redisplay it with the generated error)
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_DEVICE_ID): str
            }),
            errors=errors,
        )

    async def _async_perform_fresh_scan(self, device_id: str) -> dict[str, str]:
        """Perform a real-time mDNS browse to find the device by ID."""
        aio_zc = await ha_zeroconf.async_get_async_instance(self.hass)
        scanner = ActiveMdnsScanner(device_id)
        
        # Start an active network sweep for the NKSPAIR service type
        browser = AsyncServiceBrowser(
            aio_zc.zeroconf, 
            "_nkspair._tcp.local.", 
            handlers=[scanner.update_service]
        )
        
        try:
            # Block the UI briefly and wait up to 5 seconds for the device to respond
            await asyncio.wait_for(scanner.event.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            return {"base": "device_not_found"}
        finally:
            # Guarantee the listener is destroyed to free memory
            await browser.async_cancel()
            
        if not scanner.found_info:
            return {"base": "device_not_found"}
            
        # Verify manufacturer and model requirements
        mf = scanner.found_info.get("mf", "")
        model = scanner.found_info.get("model", "")
        if mf.upper() != "NKSPAIR" or model.upper() != "NKSPAIR_SMARTLINK":
            return {"base": "unsupported_device"}

        # Validate we successfully resolved an IP address
        if not scanner.found_info.get(CONF_HOST):
            return {"base": "device_not_found"}
            
        self.discovery_info = {
            CONF_HOST: scanner.found_info[CONF_HOST],
            CONF_PORT: scanner.found_info[CONF_PORT],
            CONF_NAME: scanner.found_info[CONF_NAME],
            CONF_DEVICE_ID: scanner.found_info[CONF_DEVICE_ID],
            CONF_MAC: scanner.found_info[CONF_MAC],
            "mdns_name": scanner.found_info["mdns_name"],
        }
        
        # Set unique ID to prevent duplicate pairings in the background
        mac = self.discovery_info[CONF_MAC]
        unique_id = mac if mac else device_id
        if unique_id:
            await self.async_set_unique_id(unique_id)
            
        return {}

    async def async_step_zeroconf(
        self, discovery_info: ha_zeroconf.ZeroconfServiceInfo
    ) -> ConfigFlowResult:
        """Handle a flow initialized by passive auto-discovery."""
        host = discovery_info.host
        port = discovery_info.port or 1884
        properties = discovery_info.properties
        mdns_name = discovery_info.name.split('.')[0]

        # Safely extract and decode TXT record fields
        def get_str(key: str, default: str = "") -> str:
            val = properties.get(key, default)
            if isinstance(val, bytes):
                val = val.decode("utf-8", errors="ignore")
            elif val is None:
                val = default
            else:
                val = str(val)
            # ESP32 C libraries often append hidden null bytes (\x00) to mDNS strings
            return val.replace("\x00", "").strip()

        device_name = get_str("name", "Smartlink Device")
        device_id = get_str("id")
        mac = get_str("mac")
        model = get_str("model")
        mf = get_str("mf")

        # Verify manufacturer and model requirements strictly
        if mf.upper() != "NKSPAIR" or model.upper() != "NKSPAIR_SMARTLINK":
            return self.async_abort(reason="unsupported_device")

        unique_id = mac if mac else device_id
        if unique_id:
            await self.async_set_unique_id(unique_id)
            # If already paired, silently update the IP and abort the UI prompt
            self._abort_if_unique_id_configured(
                updates={CONF_HOST: host, CONF_PORT: port}
            )

        self.discovery_info = {
            CONF_HOST: host,
            CONF_PORT: port,
            CONF_NAME: device_name,
            CONF_DEVICE_ID: device_id,
            CONF_MAC: mac,
            "mdns_name": mdns_name,
        }
        
        return await self.async_step_zeroconf_confirm()

    async def async_step_zeroconf_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm discovery with the user (Used by both auto and manual flows)."""
        errors = {}

        if user_input is not None:
            name = self.discovery_info[CONF_NAME]
            device_id = self.discovery_info[CONF_DEVICE_ID]
            host = self.discovery_info[CONF_HOST]
            port = self.discovery_info[CONF_PORT]

            # Verify MQTT connection before adding the device
            import aiomqtt
            
            async def _test_connection():
                async with aiomqtt.Client(hostname=host, port=port):
                    pass # Connect and immediately disconnect
                    
            try:
                await asyncio.wait_for(_test_connection(), timeout=5.0)
                
                return self.async_create_entry(
                    title=f"{name} ({device_id})",
                    data=self.discovery_info,
                )
            except (aiomqtt.MqttError, asyncio.TimeoutError, Exception):
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="zeroconf_confirm",
            description_placeholders={
                "name": self.discovery_info.get(CONF_NAME, "Unknown Device"),
                "id": self.discovery_info.get(CONF_DEVICE_ID, "Unknown ID"),
            },
            errors=errors,
        )