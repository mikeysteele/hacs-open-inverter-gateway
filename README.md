# Open Inverter Gateway for Home Assistant

Custom component to integrate Open Inverter Gateway with Home Assistant.

## Installation via HACS

1. Open HACS in Home Assistant.
2. Go to **Integrations** > **Triple Dots (top right)** > **Custom
   repositories**.
3. Paste the URL of your GitHub repository.
4. Select **Integration** as the category.
5. Click **Add**.
6. Search for "Open Inverter Gateway" and install.
7. Restart Home Assistant.

## Configuration

1. Go to **Settings** > **Devices & Services**.
2. Click **Add Integration**.
3. Search for "Open Inverter Gateway".
4. Enter your Inverter's IP address.

## Features

- **Real-time Monitoring**: Voltage, Current, Power, Energy, etc.
- **Offline Caching**: Caches last known values during the day if the inverter
  goes offline; resets to 0 at midnight.
- **Reconfigurable**: Update IP address or scan interval easily.
