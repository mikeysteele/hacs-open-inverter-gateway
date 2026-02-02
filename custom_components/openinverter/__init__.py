"""The My Open Inverter Gateway integration."""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS
from .coordinator import OpenInverterDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up My Open Inverter Gateway from a config entry."""
    _LOGGER.debug("Setting up entry %s", entry.entry_id)
    hass.data.setdefault(DOMAIN, {})

    # Create the data update coordinator
    coordinator = OpenInverterDataUpdateCoordinator(hass, entry)

    # Fetch initial data so we have it when platforms are set up.
    # This will also raise ConfigEntryNotReady if the first fetch fails.
    await coordinator.async_config_entry_first_refresh()

    # Store the coordinator instance in hass.data for platforms to access
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Set up the platforms (e.g., sensor) associated with this integration
    # The coordinator is passed implicitly via hass.data
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    _LOGGER.info("Finished setting up Open Inverter Gateway entry %s", entry.entry_id)

    # Return True to indicate successful setup
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading entry %s", entry.entry_id)

    # Unload platforms (sensor, etc.) associated with the config entry
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    # Clean up the coordinator and remove it from hass.data if platform unload was successful
    if unload_ok:
        coordinator: OpenInverterDataUpdateCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        # Ensure coordinator resources (like listeners) are released
        await coordinator.async_shutdown()
        _LOGGER.info("Successfully unloaded Open Inverter Gateway entry %s", entry.entry_id)
    else:
        _LOGGER.warning("Failed to unload platforms for entry %s", entry.entry_id)

    return unload_ok
