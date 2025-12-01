# Weather Daily Home Assistant Integration

This custom component provides sensors for average UPE and RAU values from the Hungarian daily synoptic weather report, filtered by proximity to a reference location.

## Installation

1. Copy the `weather_daily` folder to your Home Assistant `custom_components` directory.
2. Ensure you have the required Python packages: `pandas`, `pygeohash`, `requests` (Home Assistant will install them automatically).
3. Add the following to your `configuration.yaml`:

```yaml
sensor:
  - platform: weather_daily
    name: Weather Daily
```

4. Restart Home Assistant.

## Configuration
- `name`: (Optional) Prefix for the sensor names. Default: `Weather Daily`.

## Provided Sensors
- `<name> UPE`: Average UPE value (mm) for stations within 20km of the reference location.
- `<name> RAU`: Average RAU value (mm) for stations within 20km of the reference location.

## Reference Location
- The reference coordinates are hardcoded as `48.0288119, 21.7624586` (can be changed in the code).

## Development & Testing

### Running Tests
```bash
pytest tests/ --cov=. --cov-report=term-missing
```

### Code Quality
```bash
pylint daily_sensor.py hourly_sensor.py ten_minutes_sensor.py station_info_sensor.py radar_gif_image.py radar_gif_creator.py sensor.py weather_data.py image.py config_flow.py options_flow.py __init__.py coordinator.py
```

### Quality Standards
- **Test Coverage:** ≥99% (currently 99.07%)
- **Pylint Score:** 10.00/10
- **All tests must pass:** 86/86 tests passing

See [TESTING.md](TESTING.md) for comprehensive testing documentation.

## License
MIT
