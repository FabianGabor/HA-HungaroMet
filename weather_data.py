import io
import math
import zipfile
from datetime import datetime

import pandas as pd
import pytz
import requests

try:
    from .const import DEFAULT_DISTANCE_KM, URL_DAILY, URL_HOURLY, URL_TEN_MINUTES
except ImportError:
    from const import DEFAULT_DISTANCE_KM, URL_DAILY, URL_HOURLY, URL_TEN_MINUTES

from homeassistant.util import dt as dt_util
from .const import DEFAULT_DISTANCE_KM


def fetch_data(url: str) -> pd.DataFrame:
    response = requests.get(url)
    with zipfile.ZipFile(io.BytesIO(response.content)) as z:
        csv_filename = z.namelist()[0]
        with z.open(csv_filename) as csvfile:
            df = pd.read_csv(
                csvfile,
                sep=';',
                comment='/',
                skipinitialspace=True
            )
    return df

def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    df.replace(-999, pd.NA, inplace=True)
    df.columns = df.columns.str.strip()
    return df

def add_distance_column(df: pd.DataFrame, ref_lat: float, ref_lon: float) -> pd.DataFrame:
    df["Latitude"] = pd.to_numeric(df["Latitude"], errors="coerce")
    df["Longitude"] = pd.to_numeric(df["Longitude"], errors="coerce")
    df["Distance_km"] = df.apply(
        lambda row: haversine(row["Latitude"], row["Longitude"], ref_lat, ref_lon), axis=1
    )
    return df

def calculate_mean_values(df: pd.DataFrame, numeric_columns: list) -> dict:
    numeric_columns = [col for col in numeric_columns if col in df.columns]
    means = {col: (df[col].mean(skipna=True) if df[col].notna().any() else None) for col in numeric_columns}
    return means

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

def process_daily_data(hass=None, distance_km=DEFAULT_DISTANCE_KM):
    df = fetch_data(URL_DAILY)
    df = clean_data(df)
    columns = [
        "Time", "StationNumber", "StationName", "Latitude", "Longitude", "Elevation",
        "rau", "upe", "t", "tn", "tx", "sr", "et5", "et10", "et20", "et50", "et100", "tsn24"
    ]
    df = df[columns]

    try:
        ref_lat = hass.config.latitude
        ref_lon = hass.config.longitude
    except NameError:
        from local_config import ref_lat, ref_lon

    df = add_distance_column(df, ref_lat, ref_lon)
    df = df.sort_values(by="Distance_km")
    df = df[df["Distance_km"] <= distance_km]

    numeric_columns = [
        "Latitude", "Longitude", "Elevation", "rau", "upe", "t", "tn", "tx", "sr",
        "et5", "et10", "et20", "et50", "et100", "tsn24"
    ]
    means = calculate_mean_values(df, numeric_columns) 
    means["water_balance"] = means["rau"] - means["upe"] if means["rau"] is not None and means["upe"] is not None else None
    means["sr_mj"] = means["sr"] * 0.01 if means["sr"] is not None else None
    numeric_columns.append("water_balance")
    numeric_columns.append("sr_mj")

    date_iso = datetime.strptime(str(df["Time"].iloc[0]), '%Y%m%d').date().isoformat()
    station_info = df[["StationNumber", "StationName", "Latitude", "Longitude", "Elevation"]].drop_duplicates()
    station_info_list = station_info.to_dict(orient="records")
    result = {
        "time": date_iso,
        **{f"average_{col}": means[col] for col in numeric_columns},
    }
    return result, station_info_list

def process_hourly_data(hass=None, distance_km=DEFAULT_DISTANCE_KM):
    df = fetch_data(URL_HOURLY)
    df = clean_data(df)
    columns = [
        "Time", "StationNumber", "StationName", "Latitude", "Longitude", "Elevation",
        "r", "t", "ta", "tn", "tx", "u", "sg", "sr", "suv", "fs", "fsd", "fx", "fxd",
        "f", "fd", "we", "et5", "et10", "et20", "et50", "et100", "tsn", "tviz"
    ]
    df = df[columns]

    try:
        ref_lat = hass.config.latitude
        ref_lon = hass.config.longitude
    except NameError:
        from local_config import ref_lat, ref_lon

    df = add_distance_column(df, ref_lat, ref_lon)
    df = df.sort_values(by="Distance_km")
    df = df[df["Distance_km"] <= distance_km]

    numeric_columns = [
        "Latitude", "Longitude", "Elevation", "r", "t", "ta", "tn", "tx", "u", "sg", "sr", "suv", "fs", "fsd", "fx", "fxd",
        "f", "fd", "et5", "et10", "et20", "et50", "et100", "tsn", "tviz", "we"
    ]
    means = calculate_mean_values(df, numeric_columns)
    means["sr_mj"] = means["sr"] * 0.01 if means["sr"] is not None else None
    numeric_columns.append("sr_mj")

    date_str = str(df["Time"].head(1).iloc[0])
    dt_utc = datetime.strptime(date_str, '%Y%m%d%H%M').replace(tzinfo=dt_util.UTC)
    station_info = df[["StationNumber", "StationName", "Latitude", "Longitude", "Elevation"]].drop_duplicates()
    station_info_list = station_info.to_dict(orient="records")
    we_value = None
    if not df.empty and "we" in df.columns:
        we_counts = df["we"].value_counts(dropna=True)
        if not we_counts.empty:
            we_value = we_counts.idxmax()
    result = {
        "time": dt_utc.isoformat(),
        **{f"average_{col}": means[col] for col in numeric_columns},
        "we": we_value,
    }
    return result, station_info_list


def process_ten_minutes_data(hass=None, distance_km=DEFAULT_DISTANCE_KM):
    df = fetch_data(URL_TEN_MINUTES)
    df = clean_data(df)
    columns = [
        "Time", "StationNumber", "StationName", "Latitude", "Longitude", "Elevation",
        "r", "t", "ta", "tn", "tx", "u", "sg", "sr", "suv", "fs", "fsd", "fx", "fxd",
        "et5", "et10", "et20", "et50", "et100", "tsn", "tviz"
    ]
    df = df[columns]

    try:
        ref_lat = hass.config.latitude
        ref_lon = hass.config.longitude
    except NameError:
        from local_config import ref_lat, ref_lon

    df = add_distance_column(df, ref_lat, ref_lon)
    df = df.sort_values(by="Distance_km")
    df = df[df["Distance_km"] <= distance_km]

    numeric_columns = [
        "Latitude", "Longitude", "Elevation", "r", "t", "ta", "tn", "tx", "u", "sg", "sr", "suv", "fs", "fsd", "fx", "fxd",
        "et5", "et10", "et20", "et50", "et100", "tsn", "tviz"
    ]
    means = calculate_mean_values(df, numeric_columns)
    means["sr_mj"] = means["sr"] * 0.01 if means["sr"] is not None else None
    numeric_columns.append("sr_mj")

    date_str = str(df["Time"].head(1).iloc[0])
    dt_utc = datetime.strptime(date_str, '%Y%m%d%H%M').replace(tzinfo=pytz.UTC)
    station_info = df[["StationNumber", "StationName", "Latitude", "Longitude", "Elevation"]].drop_duplicates()
    station_info_list = station_info.to_dict(orient="records")
    
    result = {
        "time": dt_utc.isoformat(),
        **{f"average_{col}": means[col] for col in numeric_columns}
    }
    return result, station_info_list


if __name__ == "__main__":
    # daily_data, daily_stations = process_daily_data()
    # print("Daily Data:", daily_data)
    # print("Daily Stations:", daily_stations)

    # hourly_data, hourly_stations = process_hourly_data()
    # print("Hourly Data:", hourly_data)
    # print("Hourly Stations:", hourly_stations)

    ten_minutes_data, ten_minutes_stations = process_ten_minutes_data()
    for key, value in ten_minutes_data.items():
        print(f"{key}: {value}")
    print(f"10 perces szélsebesség: {ten_minutes_data.get('average_fs')}")
    # print("10 Minutes Stations:", ten_minutes_stations)
