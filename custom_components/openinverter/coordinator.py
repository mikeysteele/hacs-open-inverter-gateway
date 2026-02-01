"""DataUpdateCoordinator for the My Open Inverter Gateway integration."""

import logging
import async_timeout
import aiohttp
from datetime import timedelta

from homeassistant.core import HomeAssistant, callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.const import CONF_IP_ADDRESS
from homeassistant.util import dt as dt_util

from .const import DOMAIN, CONF_SCAN_INTERVAL, API_ENDPOINT_PATH

_LOGGER = logging.getLogger(__name__)

class OpenInverterDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the Open Inverter Gateway."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        """Initialize the coordinator."""
        self.hass = hass
        self.entry = entry
        self.ip_address = entry.data[CONF_IP_ADDRESS]
        # Construct the full URL to the JSON endpoint
        self.api_url = f"http://{self.ip_address}{API_ENDPOINT_PATH}"
        self.session = async_get_clientsession(hass)

        # Determine the update interval from options or initial config
        update_interval_seconds = entry.options.get(
            CONF_SCAN_INTERVAL, entry.data.get(CONF_SCAN_INTERVAL)
        )
        update_interval = timedelta(seconds=update_interval_seconds)

        _LOGGER.debug(
            "Initializing OpenInverter coordinator for %s with update interval %s",
            self.ip_address,
            update_interval,
        )

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} ({self.ip_address})",
            update_interval=update_interval,
        )

        self._last_valid_data = None
        self._last_valid_time = None

        # Listen for changes to the options flow
        self._unsub_options_update_listener = self.entry.add_update_listener(
            self._handle_options_update
        )

    @callback
    def _handle_options_update(self, hass: HomeAssistant, entry: ConfigEntry):
        """Handle options update."""
        new_interval_seconds = entry.options[CONF_SCAN_INTERVAL]
        new_interval = timedelta(seconds=new_interval_seconds)
        _LOGGER.debug(
            "Updating polling interval for %s to %s", self.ip_address, new_interval
        )
        self.update_interval = new_interval

    async def _async_update_data(self):
        """Fetch data from the API endpoint with caching support."""
        _LOGGER.debug("Attempting to fetch data from %s", self.api_url)
        try:
            # Use async_timeout for the request
            async with async_timeout.timeout(15):
                response = await self.session.get(self.api_url)
                response.raise_for_status()
                data = await response.json()
             
                # Basic validation
                if not isinstance(data, dict):
                    err_msg = f"Invalid data format received (not a dictionary): {data}"
                    _LOGGER.error(err_msg)
                    raise UpdateFailed(err_msg)

                # Update cache on success
                self._last_valid_data = data
                self._last_valid_time = dt_util.now()
                
                _LOGGER.debug("Data received from %s: %s", self.api_url, data)
                return data

        except (aiohttp.ClientError, asyncio.TimeoutError, Exception) as err:
            # If we have valid cached data, we might want to return it
            if self._last_valid_data and self._last_valid_time:
                now = dt_util.now()
                
                # Check if it's the same day
                if now.date() == self._last_valid_time.date():
                    _LOGGER.warning(
                        "Error fetching data from %s (%s). Using cached data from %s.", 
                        self.api_url, err, self._last_valid_time
                    )
                    return self._last_valid_data
                
                # If it's a new day (past midnight), reset values to 0
                else:
                    _LOGGER.warning(
                        "Error fetching data from %s (%s). New day detected, resetting values to 0.",
                        self.api_url, err
                    )
                    # Create a dictionary with all 0s matching keys of last valid data
                    # Note: We assume all values should be 0. 
                    # If there are string values, they will become 0 too, which might be odd but fits "reset" logic.
                    zero_data = {k: 0 for k in self._last_valid_data}
                    return zero_data

            # If no cache, or logic fell through, raise the error
            _LOGGER.warning("Error fetching data from %s: %s. No valid cache available.", self.api_url, err)
            raise UpdateFailed(f"Error fetching data: {err}") from err

    async def async_shutdown(self) -> None:
        """Clean up listeners when the coordinator is shut down."""
        if self._unsub_options_update_listener:
            self._unsub_options_update_listener()
        await super().async_shutdown()
