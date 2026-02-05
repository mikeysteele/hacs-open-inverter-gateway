"""DataUpdateCoordinator for the My Open Inverter Gateway integration."""

import logging
from datetime import timedelta

import aiohttp
import async_timeout
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_IP_ADDRESS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import API_ENDPOINT_PATH, CONF_SCAN_INTERVAL, DAILY_SENSORS, DOMAIN, STORAGE_KEY, STORAGE_VERSION

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
        update_interval_seconds = entry.options.get(CONF_SCAN_INTERVAL, entry.data.get(CONF_SCAN_INTERVAL))
        update_interval = timedelta(seconds=update_interval_seconds)
        self._base_update_interval = update_interval

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

        # Initialize storage
        self._store = Store(hass, STORAGE_VERSION, f"{STORAGE_KEY}.{entry.entry_id}")

        # Listen for changes to the options flow
        self._unsub_options_update_listener = self.entry.add_update_listener(self._handle_options_update)

    async def async_load_saved_data(self) -> None:
        """Load saved data from storage."""
        try:
            stored_data = await self._store.async_load()
            if stored_data:
                self._last_valid_data = stored_data.get("data")
                if timestamp := stored_data.get("timestamp"):
                    self._last_valid_time = dt_util.parse_datetime(timestamp)

                _LOGGER.debug(
                    "Loaded saved data for %s from %s. Data age: %s",
                    self.ip_address,
                    self._store.path,
                    self._last_valid_time,
                )
        except Exception as err:
            _LOGGER.warning("Error loading saved data for %s: %s", self.ip_address, err)

    async def _handle_options_update(self, hass: HomeAssistant, entry: ConfigEntry):
        """Handle options update."""
        new_interval_seconds = entry.options[CONF_SCAN_INTERVAL]
        new_interval = timedelta(seconds=new_interval_seconds)
        _LOGGER.debug("Updating polling interval for %s to %s", self.ip_address, new_interval)
        self.update_interval = new_interval
        self._base_update_interval = new_interval

    async def _async_update_data(self):
        """Fetch data from the API endpoint with selective caching support."""
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

                # Persist data
                try:
                    await self._store.async_save(
                        {
                            "data": self._last_valid_data,
                            "timestamp": self._last_valid_time.isoformat(),
                        }
                    )
                except Exception as err:
                    _LOGGER.warning("Error saving data for %s: %s", self.ip_address, err)

                # Reset backoff if needed
                if self.update_interval != self._base_update_interval:
                    _LOGGER.info(
                        "Connection to %s restored. Resetting update interval to %s",
                        self.ip_address,
                        self._base_update_interval,
                    )
                    self.update_interval = self._base_update_interval

                _LOGGER.debug("Data received from %s: %s", self.api_url, data)
                return data

        except (TimeoutError, aiohttp.ClientError, Exception) as err:
            now = dt_util.now()

            # Exponential backoff
            if self.update_interval and self.update_interval < timedelta(minutes=5):
                new_interval = self.update_interval * 2
                if new_interval > timedelta(minutes=5):
                    new_interval = timedelta(minutes=5)

                _LOGGER.warning(
                    "Error fetching data from %s: %s. Increasing update interval to %s",
                    self.api_url,
                    err,
                    new_interval,
                )
                self.update_interval = new_interval

            # Scenario 1: Same day failure -> Cache ONLY daily sensors, zero others
            if self._last_valid_data and self._last_valid_time and now.date() == self._last_valid_time.date():
                _LOGGER.warning(
                    "Error fetching data from %s (%s). Using cached data for DAILY sensors, resetting others.",
                    self.api_url,
                    err,
                )

                cached_data = {}
                for key, value in self._last_valid_data.items():
                    if key in DAILY_SENSORS:
                        cached_data[key] = value  # Keep daily values
                    else:
                        cached_data[key] = 0  # Zero out real-time values (Power, Voltage, etc.)

                return cached_data

            # Scenario 2: New day (or no cache) -> Reset EVERYTHING to 0
            elif self._last_valid_data:
                _LOGGER.warning(
                    "Error fetching data from %s (%s). New day detected (or cache invalid), resetting ALL values to 0.",
                    self.api_url,
                    err,
                )
                # Create a dictionary with all 0s
                zero_data = {k: 0 for k in self._last_valid_data}
                return zero_data

            # If no cache at all, raise the error (sensors become unavailable)
            _LOGGER.warning(
                "Error fetching data from %s: %s. No valid cache available.",
                self.api_url,
                err,
            )
            raise UpdateFailed(f"Error fetching data: {err}") from err

    async def async_shutdown(self) -> None:
        """Clean up listeners when the coordinator is shut down."""
        if self._unsub_options_update_listener:
            self._unsub_options_update_listener()
        await super().async_shutdown()
