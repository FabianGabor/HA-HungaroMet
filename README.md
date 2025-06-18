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

## License
MIT
