"""DataUpdateCoordinator for NKSPAIR Integration."""
import asyncio
import json
import logging
import aiomqtt
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, TOPIC_CONFIG, TOPIC_STATE, TOPIC_COMMAND

_LOGGER = logging.getLogger(__name__)

class DeviceDataCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """MQTT Coordinator for NKSPAIR device."""

    def __init__(self, hass: HomeAssistant, host: str, port: int, mdns_name: str) -> None:
        """Initialize the coordinator."""
        self.host = host
        self.port = port
        self.mdns_name = mdns_name
        self.config_payload: dict[str, Any] = {}
        self.device_data: dict[str, Any] = {}
        self.client = aiomqtt.Client(hostname=self.host, port=self.port, keepalive=15)
        self._config_received = asyncio.Event()
        self._task = None

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{mdns_name}",
        )

    async def async_connect(self):
        """Connect to MQTT and start listening."""
        # Start the listener task
        self._task = self.hass.async_create_task(self._listen())
        
        # Wait for config to be received before proceeding (with timeout)
        try:
            await asyncio.wait_for(self._config_received.wait(), timeout=15.0)
        except asyncio.TimeoutError:
            _LOGGER.error("Timeout waiting for config payload from %s", self.mdns_name)
            if self._task:
                self._task.cancel()
            raise UpdateFailed("Timeout waiting for configuration from device")

    async def _listen(self):
        """Listen for MQTT messages."""
        topic_config = TOPIC_CONFIG.format(mdns_name=self.mdns_name)
        topic_state = TOPIC_STATE.format(mdns_name=self.mdns_name)
        
        while True:
            try:
                async with self.client:
                    _LOGGER.info("Connected to MQTT broker at %s:%s", self.host, self.port)
                    
                    # Mark all entities as available
                    self.last_update_success = True
                    self.async_update_listeners()
                    
                    await self.client.subscribe(topic_config)
                    await self.client.subscribe(topic_state)
                    
                    # Request initial config and state
                    await self.async_send_command({"action": "get_config"})
                    await self.async_send_command({"action": "get_status"})
                    
                    async for message in self.client.messages:
                        topic = str(message.topic)
                        try:
                            payload = json.loads(message.payload.decode())
                        except ValueError:
                            _LOGGER.error("Invalid JSON received on %s", topic)
                            continue

                        if topic == topic_config:
                            _LOGGER.debug("Received config payload: %s", payload)
                            self.config_payload = payload
                            self._config_received.set()
                        elif topic == topic_state:
                            _LOGGER.debug("Received state payload: %s", payload)
                            self.device_data.update(payload)
                            self.async_set_updated_data(self.device_data)
                            
            except aiomqtt.MqttError as err:
                _LOGGER.error("MQTT connection error: %s. Reconnecting in 5 seconds...", err)
                # Mark all entities as unavailable
                self.last_update_success = False
                self.async_update_listeners()
                await asyncio.sleep(5)
            except asyncio.CancelledError:
                break
            except Exception as e:
                _LOGGER.error("Unexpected error in MQTT listener: %s", e)
                # Mark all entities as unavailable
                self.last_update_success = False
                self.async_update_listeners()
                await asyncio.sleep(5)

    async def async_send_command(self, payload: dict):
        """Send command to device."""
        topic = TOPIC_COMMAND.format(mdns_name=self.mdns_name)
        try:
            await self.client.publish(topic, payload=json.dumps(payload))
        except aiomqtt.MqttError as err:
            _LOGGER.error("Failed to send command: %s", err)

    async def async_shutdown(self):
        """Shutdown coordinator."""
        if self._task:
            self._task.cancel()