"""
Home Assistant custom component for HungaroMet weather sensors (daily, hourly, monthly).
"""

import logging
from datetime import datetime, timedelta

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_change, async_call_later
from homeassistant.helpers.typing import ConfigType
import requests
import zipfile
import io
import pandas as pd
import math
from datetime import time, timedelta, datetime
from .const import DOMAIN, DEFAULT_NAME, CONF_DISTANCE_KM, DEFAULT_DISTANCE_KM

from .const import CONF_DISTANCE_KM, DEFAULT_DISTANCE_KM, DEFAULT_NAME, DOMAIN
from .daily_sensor import HungarometWeatherDailySensor
from .hourly_sensor import HungarometWeatherHourlySensor
from .station_info_sensor import HungarometStationInfoSensor
from .ten_minutes_sensor import HungarometWeatherTenMinutesSensor
from .weather_data import (
    process_daily_data,
    process_hourly_data,
    process_ten_minutes_data,
)

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_DISTANCE_KM, default=DEFAULT_DISTANCE_KM): vol.All(
        vol.Coerce(float), vol.Range(min=1, max=100)
    ),
})

WE_CODES = {
    1: "derült",
    2: "kissé felhős",
    3: "közepesen felhős",
    4: "erősen felhős",
    5: "borult",
    6: "fátyolfelhős",
    7: "ködös",
    9: "derült, párás",
    10: "közepesen felhős, párás",
    11: "borult, párás",
    12: "erősen fátyolfelhős",
    101: "szitálás",
    102: "eső",
    103: "zápor",
    104: "zivatar esővel",
    105: "ónos szitálás",
    106: "ónos eső",
    107: "hószállingózás",
    108: "havazás",
    109: "hózápor",
    110: "havaseső",
    112: "hózivatar",
    202: "erős eső",
    203: "erős zápor",
    208: "erős havazás",
    209: "erős hózápor",
    304: "zivatar záporral",
    310: "havaseső zápor",
    500: "hófúvás",
    600: "jégeső",
    601: "dörgés",
}


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    name = config.get(CONF_NAME)
    distance_km = config.get(CONF_DISTANCE_KM, DEFAULT_DISTANCE_KM)
    sensors = []
    try:
        daily_data, station_info = await hass.async_add_executor_job(
            process_daily_data, hass, distance_km
        )
        hourly_data, _ = await hass.async_add_executor_job(process_hourly_data, hass)
        ten_minutes_data, _ = await hass.async_add_executor_job(
            process_ten_minutes_data, hass, distance_km
        )

        all_keys = set(
            list(daily_data.keys())
            + list(hourly_data.keys())
            + list(ten_minutes_data.keys())
        )
        for key in all_keys:
            unit = None
            if key in [
                "average_t",
                "average_tn",
                "average_tx",
                "average_et5",
                "average_et10",
                "average_et20",
                "average_et50",
                "average_et100",
                "average_tsn24",
                "average_ta",
                "average_tsn",
                "average_tviz",
            ]:
                unit = "°C"
            elif key in [
                "average_rau",
                "average_upe",
                "average_water_balance",
                "average_r",
            ]:
                unit = "mm"
            elif key in ["average_sr"]:
                unit = "J/cm²"
            elif key in ["average_sr_mj"]:
                unit = "MJ/m²"
            elif key in ["average_u"]:
                unit = "%"
            elif key in ["average_f", "average_fs", "average_fx"]:
                unit = "m/s"
            elif key in ["average_fd", "average_fsd", "average_fxd"]:
                unit = "°"
            elif key in ["average_sg"]:
                unit = "nSv/h"
            elif key in ["average_suv"]:
                unit = "MED"
            if key in daily_data:
                sensors.append(
                    HungarometWeatherDailySensor(hass, key, daily_data[key], unit, key)
                )
            elif key in hourly_data:
                sensors.append(
                    HungarometWeatherHourlySensor(
                        hass, key, hourly_data[key], unit, key
                    )
                )
            elif key in ten_minutes_data:
                sensors.append(
                    HungarometWeatherTenMinutesSensor(
                        hass, key, ten_minutes_data[key], unit, key
                    )
                )
        sensors.append(
            HungarometStationInfoSensor(
                hass, "HungaroMet Állomások", station_info, "platform"
            )
        )
    except Exception as e:
        _LOGGER.error(f"Failed to fetch/process weather data: {e}")
        return
    async_add_entities(sensors, True)

    # Register update service
    async def handle_update_service(call):
        for sensor in sensors:
            if sensor.hass is None or not getattr(sensor, "_added", False):
                continue
            await sensor.async_update_data()

    hass.services.async_register("hungaromet_weather", "update", handle_update_service)

    sensor_class_map = {
        "daily": HungarometWeatherDailySensor,
        "hourly": HungarometWeatherHourlySensor,
        "ten_minutes": HungarometWeatherTenMinutesSensor,
    }

    # Optimized scheduled updates - fetch once, update all sensors
    async def update_sensors_by_type(data_type: str):
        """Fetch data once and update all matching sensors."""
        target_cls = sensor_class_map.get(data_type)
        if target_cls is None:
            _LOGGER.debug(
                "HungaroMet: unsupported sensor type '%s' requested", data_type
            )
            return

        active_sensors = [
            sensor
            for sensor in sensors
            if isinstance(sensor, target_cls)
            and sensor.hass is not None
            and getattr(sensor, "_added", False)
            and hasattr(sensor, "_key")
        ]

        if not active_sensors:
            _LOGGER.debug(
                "HungaroMet: skipping %s update because no active entities are enabled",
                data_type,
            )
            return

        try:
            # Fetch data once
            if data_type == "hourly":
                data, _ = await hass.async_add_executor_job(
                    process_hourly_data, hass, DEFAULT_DISTANCE_KM
                )
            elif data_type == "ten_minutes":
                data, _ = await hass.async_add_executor_job(
                    process_ten_minutes_data, hass, DEFAULT_DISTANCE_KM
                )
            elif data_type == "daily":
                data, _ = await hass.async_add_executor_job(
                    process_daily_data, hass, DEFAULT_DISTANCE_KM
                )
            else:
                return

            # Update all matching sensors with the fetched data
            for sensor in active_sensors:
                value = data.get(sensor._key) or data.get(f"average_{sensor._key}")
                if value is None:
                    continue
                sensor._state = value
                sensor.async_write_ha_state()
        except Exception as e:
            _LOGGER.error(f"Error updating {data_type} sensors: {e}")

    # Schedule daily update
    async def check_and_reschedule_daily(now):
        await update_sensors_by_type("daily")
        time_sensor = next(
            (s for s in sensors if getattr(s, "_key", None) == "time"), None
        )
        if time_sensor and time_sensor.state:
            try:
                data_date = datetime.strptime(time_sensor.state, "%Y-%m-%d").date()
                yesterday = datetime.now().date() - timedelta(days=1)
                if data_date != yesterday:
                    _LOGGER.warning(
                        f"HungaroMet data not updated yet (got {data_date}, expected {yesterday}), will retry in 30 minutes."
                    )

                    # Schedule a one-off retry using async_call_later
                    async def retry_daily(_):
                        await check_and_reschedule_daily(None)

                    async_call_later(hass, 1800, retry_daily)
            except Exception as e:
                _LOGGER.error(f"Failed to parse date from time sensor: {e}")

    async_track_time_change(
        hass, check_and_reschedule_daily, hour=9, minute=40, second=0
    )

    # Schedule hourly update - optimized to fetch once
    async def check_and_reschedule_hourly(now):
        await update_sensors_by_type("hourly")

    async_track_time_change(hass, check_and_reschedule_hourly, minute=20, second=59)

    # Schedule ten minutes update - optimized to fetch once
    async def check_and_reschedule_ten_minutes(now):
        await update_sensors_by_type("ten_minutes")

    async_track_time_change(
        hass, check_and_reschedule_ten_minutes, minute=range(0, 60, 10), second=59
    )


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
):
    name = entry.data.get("name", "HungaroMet weather daily")
    sensors = []
    try:
        data, station_info = await hass.async_add_executor_job(
            process_daily_data, hass, DEFAULT_DISTANCE_KM
        )
        sensors.append(
            HungarometWeatherDailySensor(
                hass, "Napi mérési időpont", data["time"], None, "time"
            )
        )
        sensors.append(
            HungarometWeatherDailySensor(
                hass, "Napi párolgás", data["average_upe"], "mm", "average_upe"
            )
        )
        sensors.append(
            HungarometWeatherDailySensor(
                hass, "Napi csapadékösszeg", data["average_rau"], "mm", "average_rau"
            )
        )
        sensors.append(
            HungarometWeatherDailySensor(
                hass,
                "Napi vízegyenleg",
                data["average_water_balance"],
                "mm",
                "average_water_balance",
            )
        )
        sensors.append(
            HungarometWeatherDailySensor(
                hass, "Napi átlaghőmérséklet", data["average_t"], "°C", "t"
            )
        )
        sensors.append(
            HungarometWeatherDailySensor(
                hass, "Napi minimumhőmérséklet", data["average_tn"], "°C", "tn"
            )
        )
        sensors.append(
            HungarometWeatherDailySensor(
                hass, "Napi maximumhőmérséklet", data["average_tx"], "°C", "tx"
            )
        )
        sensors.append(
            HungarometWeatherDailySensor(
                hass, "Napi globálsugárzás összeg", data["average_sr"], "J/cm²", "sr"
            )
        )
        sensors.append(
            HungarometWeatherDailySensor(
                hass,
                "Napi globálsugárzás összeg (MJ/m²)",
                data["average_sr_mj"],
                "MJ/m²",
                "sr_mj",
            )
        )
        sensors.append(
            HungarometWeatherDailySensor(
                hass,
                "Napi átlagos 5 cm-es talajhőmérséklet",
                data["average_et5"],
                "°C",
                "et5",
            )
        )
        sensors.append(
            HungarometWeatherDailySensor(
                hass,
                "Napi átlagos 10 cm-es talajhőmérséklet",
                data["average_et10"],
                "°C",
                "et10",
            )
        )
        sensors.append(
            HungarometWeatherDailySensor(
                hass,
                "Napi átlagos 20 cm-es talajhőmérséklet",
                data["average_et20"],
                "°C",
                "et20",
            )
        )
        sensors.append(
            HungarometWeatherDailySensor(
                hass,
                "Napi átlagos 50 cm-es talajhőmérséklet",
                data["average_et50"],
                "°C",
                "et50",
            )
        )
        sensors.append(
            HungarometWeatherDailySensor(
                hass,
                "Napi átlagos 100 cm-es talajhőmérséklet",
                data["average_et100"],
                "°C",
                "et100",
            )
        )
        sensors.append(
            HungarometWeatherDailySensor(
                hass,
                "Felszínközeli hőmérséklet napi minimuma",
                data["average_tsn24"],
                "°C",
                "tsn24",
            )
        )
        sensors.append(
            HungarometStationInfoSensor(
                hass, "HungaroMet Állomások", station_info, "daily"
            )
        )

        data, station_info = await hass.async_add_executor_job(
            process_hourly_data, hass, DEFAULT_DISTANCE_KM
        )
        sensors.append(
            HungarometWeatherHourlySensor(
                hass, "Órás mérési időpont", data["time"], None, "time"
            )
        )
        sensors.append(
            HungarometWeatherHourlySensor(
                hass, "Órás csapadékösszeg", data["average_r"], "mm", "r"
            )
        )
        sensors.append(
            HungarometWeatherHourlySensor(
                hass, "Órás pillanatnyi hőmérséklet", data["average_t"], "°C", "t"
            )
        )
        sensors.append(
            HungarometWeatherHourlySensor(
                hass, "Órás átlaghőmérséklet", data["average_ta"], "°C", "ta"
            )
        )
        sensors.append(
            HungarometWeatherHourlySensor(
                hass, "Órás minimumhőmérséklet", data["average_tn"], "°C", "tn"
            )
        )
        sensors.append(
            HungarometWeatherHourlySensor(
                hass, "Órás maximumhőmérséklet", data["average_tx"], "°C", "tx"
            )
        )
        sensors.append(
            HungarometWeatherHourlySensor(
                hass, "Órás pillanatnyi relatív nedvesség", data["average_u"], "%", "u"
            )
        )
        sensors.append(
            HungarometWeatherHourlySensor(
                hass, "Órás átlagos gammadózis", data["average_sg"], "nSv/h", "sg"
            )
        )
        sensors.append(
            HungarometWeatherHourlySensor(
                hass, "Órás globálsugárzás összeg", data["average_sr"], "J/cm²", "sr"
            )
        )
        sensors.append(
            HungarometWeatherHourlySensor(
                hass,
                "Órás globálsugárzás összeg (MJ/m²)",
                data["average_sr_mj"],
                "MJ/m²",
                "sr_mj",
            )
        )
        sensors.append(
            HungarometWeatherHourlySensor(
                hass, "Órás UV sugárzás összeg", data["average_suv"], "MED", "suv"
            )
        )
        sensors.append(
            HungarometWeatherHourlySensor(
                hass, "Órás szinoptikus szélsebesség", data["average_fs"], "m/s", "fs"
            )
        )
        sensors.append(
            HungarometWeatherHourlySensor(
                hass, "Órás szinoptikus szélirány", data["average_fsd"], "°", "fsd"
            )
        )
        sensors.append(
            HungarometWeatherHourlySensor(
                hass,
                "Órás maximális széllökés sebessége",
                data["average_fx"],
                "m/s",
                "fx",
            )
        )
        sensors.append(
            HungarometWeatherHourlySensor(
                hass, "Órás maximális széllökés iránya", data["average_fxd"], "°", "fxd"
            )
        )
        sensors.append(
            HungarometWeatherHourlySensor(
                hass, "Órás átlagos szélsebesség", data["average_f"], "m/s", "f"
            )
        )
        sensors.append(
            HungarometWeatherHourlySensor(
                hass, "Órás átlagos szélirány", data["average_fd"], "°", "fd"
            )
        )
        sensors.append(
            HungarometWeatherHourlySensor(
                hass,
                "Órás felszínközeli hőmérséklet minimuma",
                data["average_tsn"],
                "C",
                "tsn",
            )
        )
        sensors.append(
            HungarometWeatherHourlySensor(
                hass,
                "Órás pillanatnyi vízhőmérséklet",
                data["average_tviz"],
                "C",
                "tviz",
            )
        )
        sensors.append(
            HungarometWeatherHourlySensor(
                hass, "Órás pillanatnyi időkép kódja", data["we"], None, "we"
            )
        )
        sensors.append(
            HungarometStationInfoSensor(
                hass, "HungaroMet Állomások", station_info, "hourly"
            )
        )

        data, station_info = await hass.async_add_executor_job(
            process_ten_minutes_data, hass, DEFAULT_DISTANCE_KM
        )
        sensors.append(
            HungarometWeatherTenMinutesSensor(
                hass, "Tízperces mérési időpont", data["time"], None, "time"
            )
        )
        sensors.append(
            HungarometWeatherTenMinutesSensor(
                hass, "Tízperces csapadékösszeg", data["average_r"], "mm", "r"
            )
        )
        sensors.append(
            HungarometWeatherTenMinutesSensor(
                hass, "Tízperces pillanatnyi hőmérséklet", data["average_t"], "°C", "t"
            )
        )
        sensors.append(
            HungarometWeatherTenMinutesSensor(
                hass, "Tízperces átlaghőmérséklet", data["average_ta"], "°C", "ta"
            )
        )
        sensors.append(
            HungarometWeatherTenMinutesSensor(
                hass, "Tízperces minimumhőmérséklet", data["average_tn"], "°C", "tn"
            )
        )
        sensors.append(
            HungarometWeatherTenMinutesSensor(
                hass, "Tízperces maximumhőmérséklet", data["average_tx"], "°C", "tx"
            )
        )
        sensors.append(
            HungarometWeatherTenMinutesSensor(
                hass,
                "Tízperces pillanatnyi relatív nedvesség",
                data["average_u"],
                "%",
                "u",
            )
        )
        sensors.append(
            HungarometWeatherTenMinutesSensor(
                hass, "Tízperces átlagos gammadózis", data["average_sg"], "nSv/h", "sg"
            )
        )
        sensors.append(
            HungarometWeatherTenMinutesSensor(
                hass,
                "Tízperces globálsugárzás összeg",
                data["average_sr"],
                "J/cm²",
                "sr",
            )
        )
        sensors.append(
            HungarometWeatherTenMinutesSensor(
                hass,
                "Tízperces globálsugárzás összeg (MJ/m²)",
                data["average_sr_mj"],
                "MJ/m²",
                "sr_mj",
            )
        )
        sensors.append(
            HungarometWeatherTenMinutesSensor(
                hass, "Tízperces UV sugárzás összeg", data["average_suv"], "MED", "suv"
            )
        )
        sensors.append(
            HungarometWeatherTenMinutesSensor(
                hass,
                "Tízperces maximális széllökés sebessége",
                data["average_fx"],
                "m/s",
                "fx",
            )
        )
        sensors.append(
            HungarometWeatherTenMinutesSensor(
                hass,
                "Tízperces maximális széllökés iránya",
                data["average_fxd"],
                "°",
                "fxd",
            )
        )
        sensors.append(
            HungarometWeatherTenMinutesSensor(
                hass, "Tízperces átlagos szélsebesség", data["average_fs"], "m/s", "fs"
            )
        )
        sensors.append(
            HungarometWeatherTenMinutesSensor(
                hass, "Tízperces átlagos szélirány", data["average_fsd"], "°", "fsd"
            )
        )
        sensors.append(
            HungarometWeatherTenMinutesSensor(
                hass,
                "Tízperces felszínközeli hőmérséklet minimuma",
                data["average_tsn"],
                "C",
                "tsn",
            )
        )
        sensors.append(
            HungarometWeatherTenMinutesSensor(
                hass,
                "Tízperces pillanatnyi vízhőmérséklet",
                data["average_tviz"],
                "C",
                "tviz",
            )
        )
        sensors.append(
            HungarometStationInfoSensor(
                hass, "HungaroMet Állomások", station_info, "ten_minutes"
            )
        )

    except Exception as e:
        _LOGGER.error(f"Failed to fetch/process weather data: {e}")
        return
    async_add_entities(sensors, True)

    async def handle_update_service(call):
        for sensor in sensors:
            if sensor.hass is None or not getattr(sensor, "_added", False):
                continue
            await sensor.async_update_data()

    hass.services.async_register(DOMAIN, "update", handle_update_service)

    sensor_class_map = {
        "daily": HungarometWeatherDailySensor,
        "hourly": HungarometWeatherHourlySensor,
        "ten_minutes": HungarometWeatherTenMinutesSensor,
    }

    # Optimized scheduled updates - fetch once, update all sensors
    async def update_sensors_by_type(data_type: str):
        """Fetch data once and update all matching sensors."""
        target_cls = sensor_class_map.get(data_type)
        if target_cls is None:
            _LOGGER.debug(
                "HungaroMet: unsupported sensor type '%s' requested", data_type
            )
            return

        active_sensors = [
            sensor
            for sensor in sensors
            if isinstance(sensor, target_cls)
            and sensor.hass is not None
            and getattr(sensor, "_added", False)
            and hasattr(sensor, "_key")
        ]

        if not active_sensors:
            _LOGGER.debug(
                "HungaroMet: skipping %s update because no active entities are enabled",
                data_type,
            )
            return

        try:
            # Fetch data once
            if data_type == "hourly":
                data, _ = await hass.async_add_executor_job(
                    process_hourly_data, hass, DEFAULT_DISTANCE_KM
                )
            elif data_type == "ten_minutes":
                data, _ = await hass.async_add_executor_job(
                    process_ten_minutes_data, hass, DEFAULT_DISTANCE_KM
                )
            elif data_type == "daily":
                data, _ = await hass.async_add_executor_job(
                    process_daily_data, hass, DEFAULT_DISTANCE_KM
                )
            else:
                return

            # Update all matching sensors with the fetched data
            for sensor in active_sensors:
                value = data.get(sensor._key) or data.get(f"average_{sensor._key}")
                if value is None:
                    continue
                sensor._state = value
                sensor.async_write_ha_state()
        except Exception as e:
            _LOGGER.error(f"Error updating {data_type} sensors: {e}")

    def schedule_update(now):
        async def check_and_reschedule():
            await update_sensors_by_type("daily")
            time_sensor = next(
                (s for s in sensors if getattr(s, "_key", None) == "time"), None
            )
            if time_sensor and time_sensor.state:
                try:
                    data_date = datetime.strptime(time_sensor.state, "%Y-%m-%d").date()
                    yesterday = datetime.now().date() - timedelta(days=1)
                    if data_date != yesterday:
                        _LOGGER.warning(
                            f"HungaroMet data not updated yet (got {data_date}, expected {yesterday}), will retry in 30 minutes."
                        )
                        async_call_later(
                            hass, 1800, lambda _: hass.add_job(check_and_reschedule)
                        )
                except Exception as e:
                    _LOGGER.error(f"Failed to parse date from time sensor: {e}")

        hass.add_job(check_and_reschedule)

    async_track_time_change(hass, schedule_update, hour=9, minute=40, second=0)

    def schedule_hourly_update(now):
        async def check_and_reschedule_hourly():
            await update_sensors_by_type("hourly")

        hass.add_job(check_and_reschedule_hourly)

    async_track_time_change(hass, schedule_hourly_update, minute=20, second=59)

    def schedule_ten_minutes_update(now):
        async def check_and_reschedule_ten_minutes():
            await update_sensors_by_type("ten_minutes")

        hass.add_job(check_and_reschedule_ten_minutes)

    async_track_time_change(
        hass, schedule_ten_minutes_update, minute=range(0, 60, 10), second=59
    )
