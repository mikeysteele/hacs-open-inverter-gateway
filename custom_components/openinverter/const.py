"""Constants for the My Open Inverter Gateway integration."""

# Domain for the integration (needs to match folder name and manifest.json)
DOMAIN = "open_inverter_gateway"

# Storage constants
STORAGE_KEY = "open_inverter_gateway.storage"
STORAGE_VERSION = 1

# Configuration keys used in config_flow and options_flow
CONF_IP_ADDRESS = "ip_address"
CONF_SCAN_INTERVAL = "scan_interval"  # User-defined refresh frequency in seconds

# Default values
DEFAULT_SCAN_INTERVAL = 60  # Default polling interval in seconds (e.g., 1 minute)

# Platforms to support (currently only sensor)
PLATFORMS = ["sensor"]

# Base URL format for the API endpoint
# Updated to use /status based on user feedback
API_ENDPOINT_PATH = "/status"

# Sensors that should be cached during the day and reset to 0 at midnight
DAILY_SENSORS = [
    "TodayGenerateEnergy",
    "PV1EnergyToday",
    "PV2EnergyToday",
    "EnergyToUserToday",
    "EnergyToGridToday",
    "DischargeEnergyToday",
    "ChargeEnergyToday",
]
