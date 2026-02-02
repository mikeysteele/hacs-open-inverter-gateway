"""Sensor platform for My Open Inverter Gateway."""

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,  # Added for RSSI
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,  # Added for kWh
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfTime,  # Added for Uptime
)

# Add other relevant constants from homeassistant.const if needed
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import OpenInverterDataUpdateCoordinator  # Import the coordinator

_LOGGER = logging.getLogger(__name__)

# ==========================================================================
# IMPORTANT: Sensor definitions based on the provided Growatt JSON sample.
# ==========================================================================
# Adapt, remove, or comment out sensors as needed.
SENSOR_DESCRIPTIONS: dict[str, SensorEntityDescription] = {
    "InverterStatus": SensorEntityDescription(
        key="InverterStatus",
        name="Inverter Status Code",  # Consider creating a template sensor later to map codes to names
        icon="mdi:information-outline",
        # No units/classes for status codes unless you map them
    ),
    "InputPower": SensorEntityDescription(
        key="InputPower",
        name="Input Power",  # Total DC power?
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:solar-power",
    ),
    "PV1Voltage": SensorEntityDescription(
        key="PV1Voltage",
        name="PV1 Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "PV1InputCurrent": SensorEntityDescription(
        key="PV1InputCurrent",
        name="PV1 Current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "PV1InputPower": SensorEntityDescription(
        key="PV1InputPower",
        name="PV1 Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "PV2Voltage": SensorEntityDescription(
        key="PV2Voltage",
        name="PV2 Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "PV2InputCurrent": SensorEntityDescription(
        key="PV2InputCurrent",
        name="PV2 Current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "PV2InputPower": SensorEntityDescription(
        key="PV2InputPower",
        name="PV2 Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "OutputPower": SensorEntityDescription(
        key="OutputPower",
        name="Output Power",  # AC power output
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:power-plug",
    ),
    "GridFrequency": SensorEntityDescription(
        key="GridFrequency",
        name="Grid Frequency",
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:sine-wave",
    ),
    "L1ThreePhaseGridVoltage": SensorEntityDescription(
        key="L1ThreePhaseGridVoltage",
        name="Grid Voltage L1",  # Assuming L1, rename if single phase
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "L1ThreePhaseGridOutputCurrent": SensorEntityDescription(
        key="L1ThreePhaseGridOutputCurrent",
        name="Grid Current L1",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "L1ThreePhaseGridOutputPower": SensorEntityDescription(
        key="L1ThreePhaseGridOutputPower",
        name="Grid Power L1",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # Add L2/L3 sensors if you have a 3-phase inverter and need them
    "TodayGenerateEnergy": SensorEntityDescription(
        key="TodayGenerateEnergy",
        name="Energy Generated Today",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,  # Assumes it resets daily
        icon="mdi:counter",
    ),
    "TotalGenerateEnergy": SensorEntityDescription(
        key="TotalGenerateEnergy",
        name="Total Energy Generated",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,  # Use TOTAL if it never resets
        icon="mdi:counter",
    ),
    "TWorkTimeTotal": SensorEntityDescription(
        key="TWorkTimeTotal",
        name="Total Work Time",  # Value seems large, might need scaling or interpretation
        native_unit_of_measurement=UnitOfTime.SECONDS,  # Assuming seconds, adjust if needed
        icon="mdi:timer-sand",
        state_class=SensorStateClass.TOTAL,  # Total runtime
        entity_registry_enabled_default=False,  # Disabled by default as unit/scale might be unclear
    ),
    "PV1EnergyToday": SensorEntityDescription(
        key="PV1EnergyToday",
        name="PV1 Energy Today",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    "PV1EnergyTotal": SensorEntityDescription(
        key="PV1EnergyTotal",
        name="PV1 Energy Total",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
    ),
    "PV2EnergyToday": SensorEntityDescription(
        key="PV2EnergyToday",
        name="PV2 Energy Today",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    "PV2EnergyTotal": SensorEntityDescription(
        key="PV2EnergyTotal",
        name="PV2 Energy Total",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
    ),
    "PVEnergyTotal": SensorEntityDescription(
        key="PVEnergyTotal",
        name="PV Energy Total (Combined)",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
    ),
    "InverterTemperature": SensorEntityDescription(
        key="InverterTemperature",
        name="Inverter Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "TemperatureInsideIPM": SensorEntityDescription(
        key="TemperatureInsideIPM",
        name="IPM Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,  # Often redundant if Inverter Temp exists
    ),
    # --- Battery Related Sensors (Add if you have a battery) ---
    "DischargePower": SensorEntityDescription(
        key="DischargePower",
        name="Battery Discharge Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:battery-arrow-down",
    ),
    "ChargePower": SensorEntityDescription(
        key="ChargePower",
        name="Battery Charge Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:battery-arrow-up",
    ),
    "BatteryVoltage": SensorEntityDescription(
        key="BatteryVoltage",
        name="Battery Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:battery",
    ),
    "SOC": SensorEntityDescription(
        key="SOC",
        name="State of Charge",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "BatteryTemperature": SensorEntityDescription(
        key="BatteryTemperature",
        name="Battery Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "BatteryState": SensorEntityDescription(
        key="BatteryState",
        name="Battery State Code",
        icon="mdi:battery-heart-variant",
        # No units/classes for status codes unless mapped
    ),
    # --- Grid/Load Interaction ---
    "ACPowerToUser": SensorEntityDescription(  # Check if this is Import from Grid or Export to Grid
        key="ACPowerToUser",
        name="AC Power To User",  # Rename for clarity (e.g., Grid Import Power?)
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:transmission-tower-import",
    ),
    "ACPowerToGrid": SensorEntityDescription(
        key="ACPowerToGrid",
        name="AC Power To Grid",  # Export Power
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:transmission-tower-export",
    ),
    "INVPowerToLocalLoad": SensorEntityDescription(
        key="INVPowerToLocalLoad",
        name="Inverter Power to Load",  # Power consumed locally from Inverter
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:home-lightning-bolt",
    ),
    "EnergyToUserToday": SensorEntityDescription(
        key="EnergyToUserToday",
        name="Energy To User Today",  # Rename for clarity (Grid Import Today?)
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    "EnergyToUserTotal": SensorEntityDescription(
        key="EnergyToUserTotal",
        name="Energy To User Total",  # Rename for clarity (Total Grid Import?)
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
    ),
    "EnergyToGridToday": SensorEntityDescription(
        key="EnergyToGridToday",
        name="Energy To Grid Today",  # Export Today
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    "EnergyToGridTotal": SensorEntityDescription(
        key="EnergyToGridTotal",
        name="Energy To Grid Total",  # Total Export
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
    ),
    "DischargeEnergyToday": SensorEntityDescription(
        key="DischargeEnergyToday",
        name="Battery Discharge Today",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    "DischargeEnergyTotal": SensorEntityDescription(
        key="DischargeEnergyTotal",
        name="Total Battery Discharge",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
    ),
    "ChargeEnergyToday": SensorEntityDescription(
        key="ChargeEnergyToday",
        name="Battery Charge Today",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    "ChargeEnergyTotal": SensorEntityDescription(
        key="ChargeEnergyTotal",
        name="Total Battery Charge",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
    ),
    # --- System Info ---
    "Uptime": SensorEntityDescription(
        key="Uptime",
        name="Device Uptime",
        native_unit_of_measurement=UnitOfTime.SECONDS,  # Assuming seconds
        icon="mdi:timer-outline",
        state_class=SensorStateClass.TOTAL_INCREASING,  # Assuming it increases and might reset
        entity_registry_enabled_default=False,  # Often less useful than HA uptime
    ),
    "WifiRSSI": SensorEntityDescription(
        key="WifiRSSI",
        name="WiFi RSSI",
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category="diagnostic",  # Mark as diagnostic
    ),
    "HeapFree": SensorEntityDescription(
        key="HeapFree",
        name="Free Heap Memory",
        native_unit_of_measurement="bytes",
        icon="mdi:memory",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category="diagnostic",
        entity_registry_enabled_default=False,
    ),
    # Add other Heap values if desired (MaxAlloc, MinFree, Fragmentation)
}
# ==========================================================================


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor entities based on a config entry."""
    coordinator: OpenInverterDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities_to_add = []
    if coordinator.data:
        # Use the Hostname from the data for the device name if available
        device_name = coordinator.data.get("Hostname", config_entry.title)

        for json_key, description in SENSOR_DESCRIPTIONS.items():
            if json_key in coordinator.data:
                _LOGGER.debug("Creating sensor for key: %s", json_key)
                entities_to_add.append(OpenInverterSensor(coordinator, config_entry, description, device_name))
            else:
                _LOGGER.debug(  # Changed to debug level, less alarming if optional keys are missing
                    "JSON key '%s' defined in SENSOR_DESCRIPTIONS not found in data from %s. Skipping sensor.",
                    json_key,
                    coordinator.ip_address,
                )
    else:
        _LOGGER.error(
            "No initial data received from coordinator for %s. Cannot set up sensors.",
            coordinator.ip_address,
        )

    if entities_to_add:
        async_add_entities(entities_to_add)
    else:
        _LOGGER.warning(
            "No sensors were added for %s. Check SENSOR_DESCRIPTIONS and device JSON output.",
            coordinator.ip_address,
        )


class OpenInverterSensor(CoordinatorEntity[OpenInverterDataUpdateCoordinator], SensorEntity):
    """Representation of an Open Inverter Sensor entity."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: OpenInverterDataUpdateCoordinator,
        config_entry: ConfigEntry,
        description: SensorEntityDescription,
        device_name: str,  # Pass device name
    ):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._config_entry = config_entry

        self._attr_unique_id = f"{config_entry.entry_id}_{description.key}"

        # Use the fetched Hostname (or fallback) for the device name
        device_info_args = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": device_name,
            "manufacturer": "Growatt",
            "configuration_url": f"http://{coordinator.ip_address}",
        }
        if mac := coordinator.data.get("Mac"):
            device_info_args["connections"] = {("mac", str(mac))}

        self._attr_device_info = DeviceInfo(**device_info_args)

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        json_key = self.entity_description.key
        value = self.coordinator.data.get(json_key)

        if value is None:
            return None  # Don't process if value is missing

        # Handle specific cases or conversions if needed
        # Example: Convert TWorkTimeTotal if it's in a weird unit
        # if json_key == "TWorkTimeTotal":
        #    try:
        #       # Assuming the value is total seconds
        #       return round(float(value) / 3600, 2) # Convert to hours
        #    except (ValueError, TypeError):
        #        return None # Handle conversion error

        # Ensure numeric types for measurement sensors
        if (
            self.entity_description.state_class == SensorStateClass.MEASUREMENT
            or self.entity_description.state_class == SensorStateClass.TOTAL
            or self.entity_description.state_class == SensorStateClass.TOTAL_INCREASING
        ):
            try:
                # Attempt conversion to float
                return float(value)
            except (ValueError, TypeError):
                _LOGGER.warning(
                    "Could not convert value '%s' for sensor '%s' (%s) to float.",
                    value,
                    self.entity_id,
                    json_key,
                )
                return None  # Return None if conversion fails

        # Return the raw value for text/status sensors or if no conversion needed
        return value

    # available property is handled by CoordinatorEntity
