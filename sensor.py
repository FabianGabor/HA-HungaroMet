"""
Home Assistant custom component for HungaroMet weather sensors (daily, hourly, monthly).
"""
import logging
import voluptuous as vol
from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorEntity
from homeassistant.const import CONF_NAME
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers import location
import homeassistant.helpers.config_validation as cv
import requests
import zipfile
import io
import pandas as pd
import math
from datetime import time, timedelta, datetime
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
from .const import DOMAIN, DEFAULT_NAME, CONF_DISTANCE_KM, DEFAULT_DISTANCE_KM


_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_DISTANCE_KM, default=DEFAULT_DISTANCE_KM): vol.All(vol.Coerce(float), vol.Range(min=1, max=100)),
})

# URL for the latest weather data
URL = "https://odp.met.hu/weather/weather_reports/synoptic/hungary/daily/csv/HABP_1D_LATEST.csv.zip"

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    name = config.get(CONF_NAME)
    distance_km = config.get(CONF_DISTANCE_KM, DEFAULT_DISTANCE_KM)
    sensors = []
    try:
        data = await hass.async_add_executor_job(fetch_and_process_data, hass, distance_km)
        sensors.append(HungarometWeatherDailySensor(hass, "Mérési időpont", data["time"], None, "time"))
        sensors.append(HungarometWeatherDailySensor(hass, "Napi párolgás", data["average_upe"], "mm", "average_upe"))
        sensors.append(HungarometWeatherDailySensor(hass, "Napi csapadékösszeg", data["average_rau"], "mm", "average_rau"))
        sensors.append(HungarometWeatherDailySensor(hass, "Napi vízegyenleg", data["water_balance"], "mm", "water_balance"))
        sensors.append(HungarometWeatherDailySensor(hass, "Napi átlaghőmérséklet", data["t"], "°C", "t"))
        sensors.append(HungarometWeatherDailySensor(hass, "Napi minimumhőmérséklet", data["tn"], "°C", "tn"))
        sensors.append(HungarometWeatherDailySensor(hass, "Napi maximumhőmérséklet", data["tx"], "°C", "tx"))
        sensors.append(HungarometWeatherDailySensor(hass, "Napi globálsugárzás összeg", data["sr"], "J/cm²", "sr"))
        sensors.append(HungarometWeatherDailySensor(hass, "Napi globálsugárzás összeg (MJ/m²)", data["sr_mj"], "MJ/m²", "sr_mj"))
        sensors.append(HungarometWeatherDailySensor(hass, "Napi átlagos 5 cm-es talajhőmérséklet", data["et5"], "°C", "et5"))
        sensors.append(HungarometWeatherDailySensor(hass, "Napi átlagos 10 cm-es talajhőmérséklet", data["et10"], "°C", "et10"))
        sensors.append(HungarometWeatherDailySensor(hass, "Napi átlagos 20 cm-es talajhőmérséklet", data["et20"], "°C", "et20"))
        sensors.append(HungarometWeatherDailySensor(hass, "Napi átlagos 50 cm-es talajhőmérséklet", data["et50"], "°C", "et50"))
        sensors.append(HungarometWeatherDailySensor(hass, "Napi átlagos 100 cm-es talajhőmérséklet", data["et100"], "°C", "et100"))
        sensors.append(HungarometWeatherDailySensor(hass, "Felszínközeli hőmérséklet napi minimuma", data["tsn24"], "°C", "tsn24"))
        sensors.append(HungarometStationInfoSensor(hass, "HungaroMet Állomások", data["station_info"]))
    except Exception as e:
        _LOGGER.error(f"Failed to fetch/process weather data: {e}")
        return
    async_add_entities(sensors, True)

    # Register update service
    async def handle_update_service(call):
        for sensor in sensors:
            await sensor.async_update_data()
    hass.services.async_register("hungaromet_weather", "update", handle_update_service)

    # Schedule daily update
    def schedule_update(now):
        async def check_and_reschedule():
            # Update all sensors
            for sensor in sensors:
                await sensor.async_update_data()
            # Find the 'Mérési időpont' sensor
            time_sensor = next((s for s in sensors if getattr(s, '_key', None) == 'time'), None)
            if time_sensor and time_sensor.state:
                try:
                    data_date = datetime.strptime(time_sensor.state, '%Y-%m-%d').date()
                    yesterday = (datetime.now().date() - timedelta(days=1))
                    if data_date != yesterday:
                        _LOGGER.warning(f"HungaroMet data not updated yet (got {data_date}, expected {yesterday}), will retry in 30 minutes.")
                        hass.helpers.event.async_call_later(1800, lambda _: hass.async_create_task(check_and_reschedule()))
                except Exception as e:
                    _LOGGER.error(f"Failed to parse date from time sensor: {e}")
        hass.async_create_task(check_and_reschedule())
    async_track_time_change(hass, schedule_update, hour=9, minute=40, second=0)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    name = entry.data.get("name", "HungaroMet weather daily")
    sensors = []
    try:
        # Use default or config value for distance_km
        data = await hass.async_add_executor_job(fetch_and_process_data, hass, DEFAULT_DISTANCE_KM)
        sensors.append(HungarometWeatherDailySensor(hass, "Mérési időpont", data["time"], None, "time"))
        sensors.append(HungarometWeatherDailySensor(hass, "Napi párolgás", data["average_upe"], "mm", "average_upe"))
        sensors.append(HungarometWeatherDailySensor(hass, "Napi csapadékösszeg", data["average_rau"], "mm", "average_rau"))
        sensors.append(HungarometWeatherDailySensor(hass, "Napi vízegyenleg", data["water_balance"], "mm", "water_balance"))
        sensors.append(HungarometWeatherDailySensor(hass, "Napi átlaghőmérséklet", data["t"], "°C", "t"))
        sensors.append(HungarometWeatherDailySensor(hass, "Napi minimumhőmérséklet", data["tn"], "°C", "tn"))
        sensors.append(HungarometWeatherDailySensor(hass, "Napi maximumhőmérséklet", data["tx"], "°C", "tx"))
        sensors.append(HungarometWeatherDailySensor(hass, "Napi globálsugárzás összeg", data["sr"], "J/cm²", "sr"))
        sensors.append(HungarometWeatherDailySensor(hass, "Napi globálsugárzás összeg (MJ/m²)", data["sr_mj"], "MJ/m²", "sr_mj"))
        sensors.append(HungarometWeatherDailySensor(hass, "Napi átlagos 5 cm-es talajhőmérséklet", data["et5"], "°C", "et5"))
        sensors.append(HungarometWeatherDailySensor(hass, "Napi átlagos 10 cm-es talajhőmérséklet", data["et10"], "°C", "et10"))
        sensors.append(HungarometWeatherDailySensor(hass, "Napi átlagos 20 cm-es talajhőmérséklet", data["et20"], "°C", "et20"))
        sensors.append(HungarometWeatherDailySensor(hass, "Napi átlagos 50 cm-es talajhőmérséklet", data["et50"], "°C", "et50"))
        sensors.append(HungarometWeatherDailySensor(hass, "Napi átlagos 100 cm-es talajhőmérséklet", data["et100"], "°C", "et100"))
        sensors.append(HungarometWeatherDailySensor(hass, "Felszínközeli hőmérséklet napi minimuma", data["tsn24"], "°C", "tsn24"))
        sensors.append(HungarometStationInfoSensor(hass, "HungaroMet Állomások", data["station_info"]))
    except Exception as e:
        _LOGGER.error(f"Failed to fetch/process weather data: {e}")
        return
    async_add_entities(sensors, True)

    async def handle_update_service(call):
        for sensor in sensors:
            await sensor.async_update_data()
    hass.services.async_register(DOMAIN, "update", handle_update_service)

    def schedule_update(now):
        async def check_and_reschedule():
            # Update all sensors
            for sensor in sensors:
                await sensor.async_update_data()
            # Find the 'Mérési időpont' sensor
            time_sensor = next((s for s in sensors if getattr(s, '_key', None) == 'time'), None)
            if time_sensor and time_sensor.state:
                try:
                    data_date = datetime.strptime(time_sensor.state, '%Y-%m-%d').date()
                    yesterday = (datetime.now().date() - timedelta(days=1))
                    if data_date != yesterday:
                        _LOGGER.warning(f"HungaroMet data not updated yet (got {data_date}, expected {yesterday}), will retry in 30 minutes.")
                        hass.helpers.event.async_call_later(1800, lambda _: hass.async_create_task(check_and_reschedule()))
                except Exception as e:
                    _LOGGER.error(f"Failed to parse date from time sensor: {e}")
        hass.async_create_task(check_and_reschedule())
    async_track_time_change(hass, schedule_update, hour=9, minute=40, second=0)


def fetch_and_process_data(hass=None, distance_km=DEFAULT_DISTANCE_KM):
    response = requests.get(URL)
    with zipfile.ZipFile(io.BytesIO(response.content)) as z:
        csv_filename = z.namelist()[0]
        with z.open(csv_filename) as csvfile:
            df = pd.read_csv(
                csvfile,
                sep=';',
                comment='/',
                skipinitialspace=True
            )
    df.columns = df.columns.str.strip()
    columns = [
        "Time", "StationNumber", "StationName", "Latitude", "Longitude", "Elevation",
        "rau", "upe", "t", "tn", "tx", "sr", "et5", "et10", "et20", "et50", "et100", "tsn24"
    ]
    df = df[columns]
    
    df["Latitude"] = pd.to_numeric(df["Latitude"], errors="coerce")
    df["Longitude"] = pd.to_numeric(df["Longitude"], errors="coerce")
    
    ref_lat = hass.config.latitude
    ref_lon = hass.config.longitude

    # Haversine function to calculate distance
    def haversine(lat1, lon1, lat2, lon2):
        R = 6371
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c
    df["Distance_km"] = df.apply(
        lambda row: haversine(row["Latitude"], row["Longitude"], ref_lat, ref_lon), axis=1
    )
    df = df.sort_values(by="Distance_km")
    df = df[df["Distance_km"] <= distance_km]
    
    upe_valid = df["upe"][df["upe"] != -999]
    rau_valid = df["rau"][df["rau"] != -999]
    t_valid = df["t"][df["t"] != -999]
    tn_valid = df["tn"][df["tn"] != -999]
    tx_valid = df["tx"][df["tx"] != -999]
    sr_valid = df["sr"][df["sr"] != -999]
    et5_valid = df["et5"][df["et5"] != -999]
    et10_valid = df["et10"][df["et10"] != -999]
    et20_valid = df["et20"][df["et20"] != -999]
    et50_valid = df["et50"][df["et50"] != -999]
    et100_valid = df["et100"][df["et100"] != -999]
    tsn24_valid = df["tsn24"][df["tsn24"] != -999]

    date_iso = datetime.strptime(str(df["Time"].iloc[0]), '%Y%m%d').date().isoformat()
    upe_mean = upe_valid.mean() if not upe_valid.empty else None
    rau_mean = rau_valid.mean() if not rau_valid.empty else None
    water_balance_mean = rau_mean - upe_mean if rau_mean is not None and upe_mean is not None else None
    t_mean = t_valid.mean() if not t_valid.empty else None
    tn_mean = tn_valid.mean() if not tn_valid.empty else None
    tx_mean = tx_valid.mean() if not tx_valid.empty else None
    sr_mean = sr_valid.mean() if not sr_valid.empty else None
    sr_mj = sr_mean * 0.01 if sr_mean is not None else None
    et5_mean = et5_valid.mean() if not et5_valid.empty else None
    et10_mean = et10_valid.mean() if not et10_valid.empty else None
    et20_mean = et20_valid.mean() if not et20_valid.empty else None
    et50_mean = et50_valid.mean() if not et50_valid.empty else None
    et100_mean = et100_valid.mean() if not et100_valid.empty else None
    tsn24_mean = tsn24_valid.mean() if not tsn24_valid.empty else None

    station_info = df[["StationNumber", "StationName"]].drop_duplicates()
    station_info_list = station_info.to_dict(orient="records")

    result = {
        "time": date_iso,
        "average_upe": upe_mean,
        "average_rau": rau_mean,
        "water_balance": water_balance_mean,
        "t": t_mean,
        "tn": tn_mean,
        "tx": tx_mean,
        "sr": sr_mean,
        "sr_mj": sr_mj,
        "et5": et5_mean,
        "et10": et10_mean,
        "et20": et20_mean,
        "et50": et50_mean,
        "et100": et100_mean,
        "tsn24": tsn24_mean,
        "station_info": station_info_list,
    }
    return result


class HungarometWeatherDailySensor(SensorEntity):
    def __init__(self, hass, name, value, unit, key):
        self.hass = hass
        self._name = name
        self._state = value
        self._unit = unit
        self._key = key
        self._device_id = "hungaromet_weather"
        self._unique_id = f"{self._device_id}_{self._name.lower().replace(' ', '_')}"
        self._added = False
    @property
    def name(self):
        return self._name
    @property
    def state(self):
        if isinstance(self._state, (int, float)):
            return round(self._state, 2)
        return self._state if self._state is not None else None
    @property
    def unit_of_measurement(self):
        return self._unit
    @property
    def device_info(self):
        return {
            "identifiers": {(self._device_id,)},
            "name": "HungaroMet",
            "manufacturer": "HungaroMet",
            "model": "Weather Sensors",
            "entry_type": "service",
        }
    @property
    def unique_id(self):
        return self._unique_id
    @property
    def entity_registry_enabled_default(self):
        # Disable sensors by default
        if self._key in ["tsn24", "et5", "et10", "et20", "et50", "et100"]:
            return False
        return True
    async def async_added_to_hass(self):
        self._added = True
        _LOGGER.debug(f"Entity {self._name} added to hass with unique_id {self._unique_id}")
    async def async_update_data(self):
        if not self._added:
            return  # Silently skip if entity not yet added
        data = await self.hass.async_add_executor_job(fetch_and_process_data, self.hass)
        if self._key in data:
            self._state = data[self._key]
        self.async_write_ha_state()
    async def async_update(self):
        await self.async_update_data()
    def update(self):
        # Not used, async_update is used instead
        pass


class HungarometStationInfoSensor(SensorEntity):
    def __init__(self, hass, name, station_info):
        self.hass = hass
        self._name = name
        self._station_info = station_info
        self._device_id = "hungaromet_weather"
        self._unique_id = f"{self._device_id}_station_info"
        self._added = False

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        # Return the number of stations as the state
        return len(self._station_info) if self._station_info is not None else 0

    @property
    def extra_state_attributes(self):
        # Return the station info as an attribute
        return {"stations": self._station_info}

    @property
    def device_info(self):
        return {
            "identifiers": {(self._device_id,)},
            "name": "HungaroMet",
            "manufacturer": "HungaroMet",
            "model": "Weather Sensors",
            "entry_type": "service",
        }

    @property
    def unique_id(self):
        return self._unique_id

    async def async_added_to_hass(self):
        self._added = True
        _LOGGER.debug(f"Entity {self._name} added to hass with unique_id {self._unique_id}")

    async def async_update_data(self):
        if not self._added:
            return
        data = await self.hass.async_add_executor_job(fetch_and_process_data, self.hass)
        if "station_info" in data:
            self._station_info = data["station_info"]
        self.async_write_ha_state()

    async def async_update(self):
        await self.async_update_data()

    def update(self):
        pass
