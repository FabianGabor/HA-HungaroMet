# HungaroMet Weather - Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/v/release/FabianGabor/HA-HungaroMet)](https://github.com/FabianGabor/HA-HungaroMet/releases)

This custom component provides weather sensors from the Hungarian Meteorological Service (HungaroMet), including daily synoptic weather reports, hourly data, 10-minute observations, and radar imagery.

## Features

- **Daily Sensors**: Average UPE and RAU values from synoptic weather reports
- **Hourly Sensors**: Hourly weather observations
- **10-Minute Sensors**: Near real-time weather data
- **Station Info**: Weather station information
- **Radar Images**: Animated radar GIF imagery

## Installation

### HACS (Recommended)

1. Open HACS in your Home Assistant instance
2. Click on "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add `https://github.com/FabianGabor/HA-HungaroMet` as a custom repository
6. Select "Integration" as the category
7. Click "Add"
8. Search for "HungaroMet Weather" and install it
9. Restart Home Assistant
10. Go to Settings → Devices & Services → Add Integration → Search for "HungaroMet Weather"

### Manual Installation

1. Copy the `custom_components/hungaromet` folder to your Home Assistant `custom_components` directory
2. Restart Home Assistant
3. Go to Settings → Devices & Services → Add Integration → Search for "HungaroMet Weather"

## Configuration

This integration is configured through the UI. After installation:

1. Go to Settings → Devices & Services
2. Click "Add Integration"
3. Search for "HungaroMet Weather"
4. Follow the configuration wizard

## Provided Sensors

- **UPE**: Precipitation values (mm) for stations near your location
- **RAU**: Additional precipitation data (mm) for stations near your location

## Development & Testing

### Running Tests

```bash
pytest tests/ --cov=custom_components/hungaromet --cov-report=term-missing
```

### Code Quality

```bash
pylint custom_components/hungaromet/
```

### Quality Standards

- **Test Coverage:** ≥100%
- **Pylint Score:** 10.00/10
- **All tests must pass:**
