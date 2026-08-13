"""Constants for My Local Integration."""

DOMAIN = "nkspair_local"
CONF_HOST = "host"
CONF_PORT = "port"
CONF_MAC = "mac"
CONF_DEVICE_ID = "device_id"
CONF_NAME = "name"
CONF_MDNS_NAME = "mdns_name"

TOPIC_CONFIG = "nkspair/{mdns_name}/config"
TOPIC_STATE = "nkspair/{mdns_name}/state"
TOPIC_COMMAND = "nkspair/{mdns_name}/command"