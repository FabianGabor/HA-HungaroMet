import builtins
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.hungaromet.daily_sensor import HungarometWeatherDailySensor
from custom_components.hungaromet.hourly_sensor import HungarometWeatherHourlySensor
from custom_components.hungaromet.radar_gif_image import HungarometRadarImage
from custom_components.hungaromet.station_info_sensor import HungarometStationInfoSensor
from custom_components.hungaromet.ten_minutes_sensor import (
    HungarometWeatherTenMinutesSensor,
)


class DummyCoordinator:
    def __init__(self, payload):
        self.data = payload


class DummyBus:
    def __init__(self):
        self.calls = []

    def async_listen_once(self, event, callback):
        self.calls.append((event, callback))


@pytest.mark.asyncio
async def test_ten_minutes_sensor_prefers_coordinator_data():
    hass = SimpleNamespace(async_add_executor_job=AsyncMock(), data={}, bus=DummyBus())
    coordinator = DummyCoordinator({"data": {"t": 12.34}})
    sensor = HungarometWeatherTenMinutesSensor(
        hass,
        name="Tízperces hőmérséklet",
        value=None,
        unit="°C",
        key="t",
        coordinator=coordinator,
    )
    sensor._added = True
    sensor.async_write_ha_state = MagicMock()

    await sensor.async_update_data()

    assert sensor._state == 12.34
    hass.async_add_executor_job.assert_not_called()
    sensor.async_write_ha_state.assert_called_once()


@pytest.mark.asyncio
async def test_hourly_sensor_fetches_when_coordinator_missing():
    hass = SimpleNamespace(
        async_add_executor_job=AsyncMock(return_value=({"t": 7.89}, None))
    )
    sensor = HungarometWeatherHourlySensor(
        hass,
        name="Órás hőmérséklet",
        value=None,
        unit="°C",
        key="t",
    )
    sensor._added = True
    sensor.async_write_ha_state = MagicMock()

    await sensor.async_update_data()

    hass.async_add_executor_job.assert_awaited_once()
    assert sensor._state == 7.89
    sensor.async_write_ha_state.assert_called_once()


def test_daily_sensor_entity_registry_defaults():
    hass = SimpleNamespace()
    disabled_key = HungarometWeatherDailySensor(
        hass,
        name="Felszínközeli minimum",
        value=0,
        unit="°C",
        key="tsn24",
    )
    enabled_key = HungarometWeatherDailySensor(
        hass,
        name="Átlaghőmérséklet",
        value=0,
        unit="°C",
        key="t",
    )

    assert disabled_key.entity_registry_enabled_default is False
    assert enabled_key.entity_registry_enabled_default is True


@pytest.mark.asyncio
async def test_daily_sensor_skips_update_when_not_added():
    hass = SimpleNamespace(async_add_executor_job=AsyncMock())
    sensor = HungarometWeatherDailySensor(
        hass,
        name="Napi átlag",
        value=None,
        unit="°C",
        key="t",
    )

    await sensor.async_update_data()

    hass.async_add_executor_job.assert_not_called()


@pytest.mark.asyncio
async def test_daily_sensor_uses_coordinator_payload():
    hass = SimpleNamespace(async_add_executor_job=AsyncMock())
    sensor = HungarometWeatherDailySensor(
        hass,
        name="Napi átlag",
        value=None,
        unit="°C",
        key="t",
        coordinator=DummyCoordinator({"data": {"t": 42}}),
    )
    sensor._added = True
    sensor.async_write_ha_state = MagicMock()

    await sensor.async_update_data()

    assert sensor._state == 42
    hass.async_add_executor_job.assert_not_called()
    sensor.async_write_ha_state.assert_called_once()


@pytest.mark.asyncio
async def test_daily_sensor_async_update_delegates_to_update_data():
    sensor = HungarometWeatherDailySensor(SimpleNamespace(), "Daily", 0, "°C", "t")
    sensor.async_update_data = AsyncMock()

    await sensor.async_update()

    sensor.async_update_data.assert_awaited_once()


def test_daily_sensor_sync_update_is_noop():
    sensor = HungarometWeatherDailySensor(SimpleNamespace(), "Daily", 0, "°C", "t")

    assert sensor.update() is None


@pytest.mark.asyncio
async def test_radar_image_updates_only_when_added(tmp_path):
    gif_dir = tmp_path / "www"
    gif_dir.mkdir()
    gif_file = gif_dir / "radar_animation.gif"
    gif_file.write_bytes(b"gif data")

    hass = SimpleNamespace(async_add_executor_job=AsyncMock(), data={}, bus=DummyBus())
    image = HungarometRadarImage(hass)
    image._gif_path = str(gif_file)
    image.async_write_ha_state = MagicMock()

    await image.async_update_data()
    hass.async_add_executor_job.assert_not_called()

    image._added = True
    await image.async_update_data()

    hass.async_add_executor_job.assert_awaited_once()
    assert image._update_counter == 1
    image.async_write_ha_state.assert_called()


@pytest.mark.asyncio
async def test_ten_minutes_sensor_no_update_when_not_added():
    hass = SimpleNamespace(async_add_executor_job=AsyncMock())
    sensor = HungarometWeatherTenMinutesSensor(
        hass,
        name="Tízperces hőmérséklet",
        value=None,
        unit="°C",
        key="t",
    )

    await sensor.async_update_data()

    hass.async_add_executor_job.assert_not_called()


@pytest.mark.asyncio
async def test_daily_sensor_uses_average_key_when_direct_missing():
    hass = SimpleNamespace(
        async_add_executor_job=AsyncMock(return_value=({"average_t": 18.5}, None))
    )
    sensor = HungarometWeatherDailySensor(
        hass,
        name="Napi átlag",
        value=None,
        unit="°C",
        key="t",
    )
    sensor._added = True
    sensor.async_write_ha_state = MagicMock()

    await sensor.async_update_data()

    assert sensor._state == 18.5
    sensor.async_write_ha_state.assert_called_once()


@pytest.mark.asyncio
async def test_station_info_sensor_updates_station_list():
    hass = SimpleNamespace(
        async_add_executor_job=AsyncMock(return_value=({}, ["AAA", "BBB"]))
    )
    sensor = HungarometStationInfoSensor(hass, "Stations", [], "daily")
    sensor._added = True
    sensor.async_write_ha_state = MagicMock()

    await sensor.async_update_data()

    hass.async_add_executor_job.assert_awaited_once()
    assert sensor.state == 2
    assert sensor.extra_state_attributes["stations"] == ["AAA", "BBB"]
    sensor.async_write_ha_state.assert_called_once()


@pytest.mark.asyncio
async def test_radar_image_schedules_and_unsubscribes(monkeypatch):
    captured = {}

    def fake_track(hass, callback, **kwargs):
        captured["kwargs"] = kwargs
        captured["callback"] = callback

        def _unsub():
            captured["unsub"] = True

        return _unsub

    monkeypatch.setattr(
        "custom_components.hungaromet.radar_gif_image.async_track_time_change",
        fake_track,
    )

    hass = SimpleNamespace(async_add_executor_job=AsyncMock(), data={}, bus=DummyBus())
    image = HungarometRadarImage(hass)

    await image.async_added_to_hass()
    assert image._unsub_update is not None
    assert captured["kwargs"]["minute"] == [
        1,
        6,
        11,
        16,
        21,
        26,
        31,
        36,
        41,
        46,
        51,
        56,
    ]

    await image.async_will_remove_from_hass()
    assert captured.get("unsub") is True


def test_daily_sensor_state_and_metadata():
    hass = SimpleNamespace()
    sensor = HungarometWeatherDailySensor(
        hass,
        name="Átlaghőmérséklet",
        value=12.3456,
        unit="°C",
        key="t",
    )

    assert sensor.name == "Átlaghőmérséklet"
    assert sensor.state == 12.35
    sensor._state = None
    assert sensor.state is None
    assert sensor.unit_of_measurement == "°C"
    assert sensor.device_info["name"] == "HungaroMet"
    assert sensor.unique_id.endswith("átlaghőmérséklet".replace(" ", "_"))


def test_hourly_sensor_time_conversion(monkeypatch):
    hass = SimpleNamespace()
    sensor = HungarometWeatherHourlySensor(
        hass,
        name="Idő",
        value="2024-01-01T12:34:56",
        unit="",
        key="time",
    )

    monkeypatch.setattr(
        "custom_components.hungaromet.hourly_sensor.dt_util.as_local",
        lambda dt: dt,
    )

    assert sensor.state == "2024-01-01 12:34"
    sensor._state = "invalid"
    assert sensor.state == "invalid"


@pytest.mark.asyncio
async def test_hourly_sensor_uses_average_if_needed():
    hass = SimpleNamespace(async_add_executor_job=AsyncMock(return_value=({}, None)))
    sensor = HungarometWeatherHourlySensor(
        hass,
        name="Órás hőmérséklet",
        value=None,
        unit="°C",
        key="t",
    )
    sensor._added = True
    sensor.async_write_ha_state = MagicMock()

    sensor.coordinator = DummyCoordinator({"data": {"average_t": 21.5}})
    await sensor.async_update_data()

    assert sensor._state == 21.5
    hass.async_add_executor_job.assert_not_called()


def test_hourly_sensor_metadata_properties():
    hass = SimpleNamespace()
    sensor = HungarometWeatherHourlySensor(
        hass,
        name="Órás",
        value=1.234,
        unit="°C",
        key="t",
    )

    assert sensor.unit_of_measurement == "°C"
    assert sensor.device_info["manufacturer"] == "HungaroMet"
    assert sensor.state == 1.23


def test_hourly_sensor_returns_none_without_state():
    hass = SimpleNamespace()
    sensor = HungarometWeatherHourlySensor(hass, "Órás", None, "°C", "tn")

    assert sensor.state is None


def test_hourly_sensor_time_conversion_failure_returns_raw():
    hass = SimpleNamespace()
    sensor = HungarometWeatherHourlySensor(hass, "Time", "bad", "", "time")

    assert sensor.state == "bad"


def test_hourly_sensor_name_and_unique_id():
    hass = SimpleNamespace()
    sensor = HungarometWeatherHourlySensor(hass, "Órás", 0, "°C", "t")

    assert sensor.name == "Órás"
    assert sensor.unique_id.startswith("hungaromet_weather_hourly_")
    assert sensor.device_info["name"] == "HungaroMet órás"


@pytest.mark.asyncio
async def test_hourly_sensor_skips_update_when_not_added():
    hass = SimpleNamespace(async_add_executor_job=AsyncMock())
    sensor = HungarometWeatherHourlySensor(hass, "Órás", None, "°C", "t")

    await sensor.async_update_data()

    hass.async_add_executor_job.assert_not_called()


@pytest.mark.asyncio
async def test_hourly_sensor_async_update_delegates_to_update_data():
    sensor = HungarometWeatherHourlySensor(SimpleNamespace(), "Órás", 0, "°C", "t")
    sensor.async_update_data = AsyncMock()

    await sensor.async_update()

    sensor.async_update_data.assert_awaited_once()


def test_hourly_sensor_sync_update_is_noop():
    sensor = HungarometWeatherHourlySensor(SimpleNamespace(), "Órás", 0, "°C", "t")

    assert sensor.update() is None


@pytest.mark.asyncio
async def test_ten_minutes_sensor_uses_average_if_needed():
    hass = SimpleNamespace(
        async_add_executor_job=AsyncMock(return_value=({"average_t": 11.1}, None))
    )
    sensor = HungarometWeatherTenMinutesSensor(
        hass,
        name="Tízperces hőmérséklet",
        value=None,
        unit="°C",
        key="t",
    )
    sensor._added = True
    sensor.async_write_ha_state = MagicMock()

    await sensor.async_update_data()

    assert sensor._state == 11.1
    sensor.async_write_ha_state.assert_called_once()


def test_ten_minutes_sensor_time_conversion(monkeypatch):
    hass = SimpleNamespace()
    sensor = HungarometWeatherTenMinutesSensor(
        hass,
        name="Idő",
        value="2024-01-01T06:00:00",
        unit="",
        key="time",
    )

    monkeypatch.setattr(
        "custom_components.hungaromet.ten_minutes_sensor.dt_util.as_local",
        lambda dt: dt,
    )

    assert sensor.state == "2024-01-01 06:00"


def test_ten_minutes_sensor_name_and_unique_id():
    hass = SimpleNamespace()
    sensor = HungarometWeatherTenMinutesSensor(hass, "Ten", 0, "°C", "t")

    assert sensor.name == "Ten"
    assert sensor.unique_id.startswith("hungaromet_weather_ten_minutes_")
    assert sensor.unit_of_measurement == "°C"
    assert sensor.device_info["manufacturer"] == "HungaroMet"


def test_ten_minutes_sensor_time_conversion_failure_returns_raw():
    hass = SimpleNamespace()
    sensor = HungarometWeatherTenMinutesSensor(hass, "Idő", "invalid", "", "time")

    assert sensor.state == "invalid"


def test_ten_minutes_sensor_state_none_when_missing():
    hass = SimpleNamespace()
    sensor = HungarometWeatherTenMinutesSensor(hass, "Ten", None, "°C", "f")

    assert sensor.state is None


def test_ten_minutes_sensor_rounds_numeric_state():
    hass = SimpleNamespace()
    sensor = HungarometWeatherTenMinutesSensor(hass, "Ten", 1.2345, "°C", "t")

    assert sensor.state == 1.23


@pytest.mark.asyncio
async def test_ten_minutes_sensor_async_update_delegates_to_update_data():
    sensor = HungarometWeatherTenMinutesSensor(SimpleNamespace(), "Ten", 0, "°C", "t")
    sensor.async_update_data = AsyncMock()

    await sensor.async_update()

    sensor.async_update_data.assert_awaited_once()


def test_ten_minutes_sensor_sync_update_is_noop():
    sensor = HungarometWeatherTenMinutesSensor(SimpleNamespace(), "Ten", 0, "°C", "t")

    assert sensor.update() is None


@pytest.mark.asyncio
async def test_station_info_lifecycle(monkeypatch):
    hass = SimpleNamespace(async_add_executor_job=AsyncMock(return_value=({}, [])))
    sensor = HungarometStationInfoSensor(hass, "Stations", [], "daily")

    await sensor.async_added_to_hass()
    assert sensor._added is True

    await sensor.async_will_remove_from_hass()
    assert sensor._added is False


def test_station_info_properties():
    hass = SimpleNamespace(async_add_executor_job=AsyncMock())
    sensor = HungarometStationInfoSensor(hass, "Stations", ["A"], "daily")

    assert sensor.name == "Stations"
    assert sensor.state == 1
    assert sensor.extra_state_attributes["stations"] == ["A"]
    assert sensor.device_info["model"] == "Napi időjárás szenzorok"
    assert sensor.unique_id.endswith("daily")


@pytest.mark.asyncio
async def test_station_info_sensor_skips_update_when_not_added():
    hass = SimpleNamespace(async_add_executor_job=AsyncMock())
    sensor = HungarometStationInfoSensor(hass, "Stations", [], "daily")

    await sensor.async_update_data()

    hass.async_add_executor_job.assert_not_called()


@pytest.mark.asyncio
async def test_station_info_sensor_async_update_delegates_to_update_data():
    sensor = HungarometStationInfoSensor(SimpleNamespace(), "Stations", [], "daily")
    sensor.async_update_data = AsyncMock()

    await sensor.async_update()

    sensor.async_update_data.assert_awaited_once()


def test_station_info_sensor_sync_update_is_noop():
    sensor = HungarometStationInfoSensor(SimpleNamespace(), "Stations", [], "daily")

    assert sensor.update() is None


@pytest.mark.asyncio
async def test_radar_async_image_missing(tmp_path):
    hass = SimpleNamespace(async_add_executor_job=AsyncMock(), data={}, bus=DummyBus())
    image = HungarometRadarImage(hass)
    image._gif_path = str(tmp_path / "missing.gif")

    result = await image.async_image()
    assert result is None


def test_radar_sync_image_reads_file(tmp_path):
    gif_file = tmp_path / "radar_animation.gif"
    gif_file.write_bytes(b"binary")
    hass = SimpleNamespace(async_add_executor_job=AsyncMock(), data={}, bus=DummyBus())
    image = HungarometRadarImage(hass)
    image._gif_path = str(gif_file)

    assert image.image() == b"binary"


def test_radar_image_property_helpers(tmp_path):
    hass = SimpleNamespace(async_add_executor_job=AsyncMock(), data={}, bus=DummyBus())
    image = HungarometRadarImage(hass, name="Custom Radar")
    image._gif_path = str(tmp_path / "missing.gif")

    assert image.name == "Custom Radar"
    assert image.unique_id.endswith("custom_radar")
    assert image.device_info["model"] == "Radar Image"
    assert image.state == "unknown"
    assert image.available is False
    assert image.extra_state_attributes == {"last_updated": None, "update_counter": 0}


@pytest.mark.asyncio
async def test_radar_handle_scheduled_update_ignores_when_not_added(monkeypatch):
    hass = SimpleNamespace(async_add_executor_job=AsyncMock(), data={}, bus=DummyBus())
    image = HungarometRadarImage(hass)
    image.async_update_data = AsyncMock()

    await image._handle_scheduled_update(None)

    image.async_update_data.assert_not_awaited()


@pytest.mark.asyncio
async def test_radar_async_update_delegates_to_update_data():
    hass = SimpleNamespace(async_add_executor_job=AsyncMock(), data={}, bus=DummyBus())
    image = HungarometRadarImage(hass)
    image.async_update_data = AsyncMock()

    await image.async_update()

    image.async_update_data.assert_awaited_once()


@pytest.mark.asyncio
async def test_radar_async_image_reads_file(tmp_path):
    hass = SimpleNamespace(async_add_executor_job=AsyncMock(), data={}, bus=DummyBus())
    image = HungarometRadarImage(hass)
    gif_file = tmp_path / "radar_async.gif"
    gif_file.write_bytes(b"async")
    image._gif_path = str(gif_file)

    result = await image.async_image()

    assert result == b"async"


@pytest.mark.asyncio
async def test_radar_async_image_os_error_returns_none(tmp_path, monkeypatch):
    hass = SimpleNamespace(async_add_executor_job=AsyncMock(), data={}, bus=DummyBus())
    image = HungarometRadarImage(hass)
    gif_file = tmp_path / "radar_async_error.gif"
    gif_file.write_bytes(b"data")
    image._gif_path = str(gif_file)
    real_open = builtins.open

    def _raise(path, *args, mode="r", **kwargs):
        if path == str(gif_file):
            raise OSError("boom")
        return real_open(path, *args, mode=mode, **kwargs)

    monkeypatch.setattr(builtins, "open", _raise)

    assert await image.async_image() is None


def test_radar_sync_image_missing_returns_none(tmp_path):
    hass = SimpleNamespace(async_add_executor_job=AsyncMock(), data={}, bus=DummyBus())
    image = HungarometRadarImage(hass)
    image._gif_path = str(tmp_path / "nope.gif")

    assert image.image() is None


def test_radar_sync_image_os_error_returns_none(tmp_path, monkeypatch):
    hass = SimpleNamespace(async_add_executor_job=AsyncMock(), data={}, bus=DummyBus())
    image = HungarometRadarImage(hass)
    gif_file = tmp_path / "radar_sync_error.gif"
    gif_file.write_bytes(b"data")
    image._gif_path = str(gif_file)
    real_open = builtins.open

    def _raise(path, *args, mode="r", **kwargs):
        if path == str(gif_file):
            raise OSError("boom")
        return real_open(path, *args, mode=mode, **kwargs)

    monkeypatch.setattr(builtins, "open", _raise)

    assert image.image() is None


def test_radar_image_initializes_with_existing_file(monkeypatch):
    hass = SimpleNamespace(async_add_executor_job=AsyncMock(), data={}, bus=DummyBus())
    monkeypatch.setattr(
        "custom_components.hungaromet.radar_gif_image.os.path.exists",
        lambda path: True,
    )
    monkeypatch.setattr(
        "custom_components.hungaromet.radar_gif_image.os.path.getmtime",
        lambda path: datetime(2024, 1, 1, 0, 0).timestamp(),
    )

    image = HungarometRadarImage(hass)

    assert image.state.startswith("2024-01-01")
    assert image.available is True


@pytest.mark.asyncio
async def test_radar_handle_scheduled_update(monkeypatch):
    hass = SimpleNamespace(async_add_executor_job=AsyncMock(), data={}, bus=DummyBus())
    image = HungarometRadarImage(hass)
    image._added = True
    called = AsyncMock()
    monkeypatch.setattr(image, "async_update_data", called)

    await image._handle_scheduled_update(None)
    called.assert_awaited_once()


@pytest.mark.asyncio
async def test_daily_sensor_lifecycle():
    hass = SimpleNamespace()
    sensor = HungarometWeatherDailySensor(hass, "Daily", 0, "°C", "t")

    await sensor.async_added_to_hass()
    assert sensor._added is True

    await sensor.async_will_remove_from_hass()
    assert sensor._added is False


@pytest.mark.asyncio
async def test_hourly_sensor_lifecycle():
    hass = SimpleNamespace()
    sensor = HungarometWeatherHourlySensor(hass, "Hourly", 0, "°C", "t")

    await sensor.async_added_to_hass()
    assert sensor._added is True

    await sensor.async_will_remove_from_hass()
    assert sensor._added is False


@pytest.mark.asyncio
async def test_ten_minutes_sensor_lifecycle():
    hass = SimpleNamespace()
    sensor = HungarometWeatherTenMinutesSensor(hass, "Ten", 0, "°C", "t")

    await sensor.async_added_to_hass()
    assert sensor._added is True

    await sensor.async_will_remove_from_hass()
    assert sensor._added is False
