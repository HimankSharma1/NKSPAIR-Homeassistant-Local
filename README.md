# NKSPAIR Smart

**Visible comfort. Invisible tech.**

NKSPAIR Smart is a custom integration for Home Assistant that provides local control for NKSPAIR Smart devices over MQTT.

## Features
- **Local Push**: Instantly updates device state without relying on cloud polling.
- **MQTT**: Fast and reliable communication via standard MQTT protocol.
- **Auto-Discovery**: Devices and entities are automatically configured and added to Home Assistant.

## Installation

### HACS (Recommended)
1. Open HACS in your Home Assistant instance.
2. Go to Integrations > Explore & Add Repositories.
3. Search for "NKSPAIR Smart" (or add this repository as a custom repository).
4. Click Install.
5. Restart Home Assistant.

### Manual Configuration
1. Download the latest release from the repository.
2. Extract the `custom_components/nkspair_local` folder into your Home Assistant's `config/custom_components` directory.
3. Restart Home Assistant.
