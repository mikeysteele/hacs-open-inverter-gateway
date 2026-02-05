from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.const import CONF_IP_ADDRESS, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.openinverter.coordinator import OpenInverterDataUpdateCoordinator

# Mock data
MOCK_IP = "192.168.1.100"
MOCK_CONFIG_DATA = {CONF_IP_ADDRESS: MOCK_IP}
MOCK_OPTIONS_DATA = {CONF_SCAN_INTERVAL: 10}


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {}
    return hass


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    entry = MagicMock()
    entry.data = MOCK_CONFIG_DATA
    entry.options = MOCK_OPTIONS_DATA
    entry.title = "Test Inverter"
    return entry


@pytest.fixture
def mock_session():
    """Mock aiohttp session."""
    with patch("custom_components.openinverter.coordinator.async_get_clientsession") as mock_ws:
        session = MagicMock()
        mock_ws.return_value = session
        yield session


@pytest.fixture(autouse=True)
def mock_store():
    """Mock the storage to prevent file access and config errors."""
    with patch("custom_components.openinverter.coordinator.Store") as MockStore:
        store = MockStore.return_value
        store.async_load = AsyncMock(return_value=None)
        store.async_save = AsyncMock()
        yield MockStore


@pytest.mark.asyncio
async def test_initial_interval(mock_hass, mock_config_entry, mock_session):
    """Test initial update interval is set correctly."""
    coordinator = OpenInverterDataUpdateCoordinator(mock_hass, mock_config_entry)

    assert coordinator.update_interval == timedelta(seconds=10)
    assert coordinator._base_update_interval == timedelta(seconds=10)


@pytest.mark.asyncio
async def test_exponential_backoff_on_timeout(mock_hass, mock_config_entry, mock_session):
    """Test standard exponential backoff."""
    coordinator = OpenInverterDataUpdateCoordinator(mock_hass, mock_config_entry)

    # Simulate first failure
    mock_session.get.side_effect = TimeoutError()

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()

    # Interval should double: 10 * 2 = 20
    assert coordinator.update_interval == timedelta(seconds=20)

    # Simulate second failure
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()

    # Interval should double again: 20 * 2 = 40
    assert coordinator.update_interval == timedelta(seconds=40)


@pytest.mark.asyncio
async def test_backoff_cap(mock_hass, mock_config_entry, mock_session):
    """Test backoff doesn't exceed 5 minutes."""
    coordinator = OpenInverterDataUpdateCoordinator(mock_hass, mock_config_entry)
    # Set interval close to max to test cap
    coordinator.update_interval = timedelta(minutes=4)

    mock_session.get.side_effect = TimeoutError()

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()

    # Should be capped at 5 mins, not 8 mins
    assert coordinator.update_interval == timedelta(minutes=5)


class FakeResponse:
    def __init__(self, data, status=200):
        self._data = data
        self.status = status

    def raise_for_status(self):
        pass

    async def json(self):
        return self._data

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


@pytest.mark.asyncio
async def test_reset_on_success(mock_hass, mock_config_entry, mock_session):
    """Test interval resets to base on success."""
    coordinator = OpenInverterDataUpdateCoordinator(mock_hass, mock_config_entry)

    # Simulate failure to increase interval
    mock_session.get.side_effect = TimeoutError()
    try:
        await coordinator._async_update_data()
    except UpdateFailed:
        pass

    assert coordinator.update_interval == timedelta(seconds=20)

    # Simulate success
    mock_session.get.side_effect = None
    fake_response = FakeResponse({"Mac": "11:22:33:44:55:66"})

    # session.get() updates return value to be awaitable
    mock_session.get = AsyncMock(return_value=fake_response)

    await coordinator._async_update_data()

    # Should handle reset
    assert coordinator.update_interval == timedelta(seconds=10)


@pytest.mark.asyncio
async def test_persistence_load_and_save(mock_hass, mock_config_entry, mock_session):
    """Test data is loaded from and saved to storage."""

    # Mock Store
    with patch("custom_components.openinverter.coordinator.Store") as MockStore:
        mock_store_instance = MockStore.return_value
        # Setup async_load to return mocked data
        mock_store_instance.async_load = AsyncMock(
            return_value={"data": {"Mac": "AA:BB:CC:DD:EE:FF"}, "timestamp": "2023-10-27T10:00:00+00:00"}
        )
        mock_store_instance.async_save = AsyncMock()

        coordinator = OpenInverterDataUpdateCoordinator(mock_hass, mock_config_entry)

        # Test loading
        await coordinator.async_load_saved_data()

        assert coordinator._last_valid_data == {"Mac": "AA:BB:CC:DD:EE:FF"}
        assert str(coordinator._last_valid_time) == "2023-10-27 10:00:00+00:00"

        # Test saving on successful update
        mock_session.get.side_effect = None
        fake_response = FakeResponse({"Mac": "11:22:33:44:55:66"})
        mock_session.get = AsyncMock(return_value=fake_response)

        await coordinator._async_update_data()

        # Verify async_save was called
        mock_store_instance.async_save.assert_called_once()
        save_call_args = mock_store_instance.async_save.call_args[0][0]
        assert save_call_args["data"] == {"Mac": "11:22:33:44:55:66"}
        assert "timestamp" in save_call_args
