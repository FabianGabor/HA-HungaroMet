"""Tests for weather_data.py"""

import io
import zipfile
from unittest.mock import Mock, patch

import pandas as pd
import pytest

from custom_components.hungaromet.weather_data import (
    _get_reference_coords,
    fetch_data,
    clean_data,
    add_distance_column,
    calculate_mean_values,
    haversine,
    process_daily_data,
    process_hourly_data,
    process_ten_minutes_data,
)


def test_haversine_same_location():
    """Test haversine distance for same location is zero."""
    distance = haversine(47.5, 19.0, 47.5, 19.0)
    assert distance == pytest.approx(0.0, abs=0.1)


def test_haversine_known_distance():
    """Test haversine with known distance (Budapest to Debrecen approximately 200km)."""
    # Budapest coords: 47.4979, 19.0402
    # Debrecen coords: 47.5316, 21.6273
    distance = haversine(47.4979, 19.0402, 47.5316, 21.6273)
    assert distance == pytest.approx(200, abs=10)  # Roughly 200km


def test_get_reference_coords_from_hass():
    """Test getting reference coordinates from hass."""
    hass = Mock()
    hass.config.latitude = 47.5
    hass.config.longitude = 19.0

    lat, lon = _get_reference_coords(hass)

    assert lat == 47.5
    assert lon == 19.0


def test_get_reference_coords_no_hass_no_local_config():
    """Test getting reference coordinates without hass or local_config raises ValueError."""
    with pytest.raises(ValueError, match="Reference coordinates are unavailable"):
        _get_reference_coords(None)


def test_clean_data():
    """Test clean_data replaces -999 with NA and strips column names."""
    df = pd.DataFrame({" Temperature ": [20, -999, 25], " Humidity ": [60, 70, -999]})

    result = clean_data(df)

    assert "Temperature" in result.columns
    assert "Humidity" in result.columns
    assert pd.isna(result["Temperature"].iloc[1])
    assert pd.isna(result["Humidity"].iloc[2])
    assert result["Temperature"].iloc[0] == 20


def test_add_distance_column():
    """Test add_distance_column calculates distances correctly."""
    df = pd.DataFrame({
        "Latitude": [47.5, 47.6, 47.4],
        "Longitude": [19.0, 19.1, 18.9],
        "StationName": ["A", "B", "C"],
    })

    result = add_distance_column(df, 47.5, 19.0)

    assert "Distance_km" in result.columns
    assert result["Distance_km"].iloc[0] == pytest.approx(0.0, abs=0.1)
    assert result["Distance_km"].iloc[1] > 0
    assert result["Distance_km"].iloc[2] > 0


def test_calculate_mean_values_all_valid():
    """Test calculate_mean_values with all valid data."""
    df = pd.DataFrame({
        "temp": [20, 22, 21],
        "humidity": [60, 70, 65],
        "pressure": [1013, 1015, 1014],
    })

    result = calculate_mean_values(df, ["temp", "humidity", "pressure"])

    assert result["temp"] == pytest.approx(21.0, abs=0.1)
    assert result["humidity"] == pytest.approx(65.0, abs=0.1)
    assert result["pressure"] == pytest.approx(1014.0, abs=0.1)


def test_calculate_mean_values_with_na():
    """Test calculate_mean_values skips NA values."""
    df = pd.DataFrame({"temp": [20, pd.NA, 22], "humidity": [60, 70, pd.NA]})

    result = calculate_mean_values(df, ["temp", "humidity"])

    assert result["temp"] == pytest.approx(21.0, abs=0.1)
    assert result["humidity"] == pytest.approx(65.0, abs=0.1)


def test_calculate_mean_values_all_na():
    """Test calculate_mean_values returns None for all NA."""
    df = pd.DataFrame({"temp": [pd.NA, pd.NA, pd.NA]})

    result = calculate_mean_values(df, ["temp"])

    assert result["temp"] is None


def test_calculate_mean_values_missing_column():
    """Test calculate_mean_values skips missing columns."""
    df = pd.DataFrame({"temp": [20, 22, 21]})

    result = calculate_mean_values(df, ["temp", "missing_col"])

    assert "temp" in result
    assert "missing_col" not in result
    assert result["temp"] == pytest.approx(21.0, abs=0.1)


@patch("custom_components.hungaromet.weather_data.requests.get")
def test_fetch_data_success(mock_get):
    """Test fetch_data successfully downloads and parses data."""
    # Create a CSV content
    csv_content = """Time;StationNumber;Temperature
20240101;1234;20.5
20240101;5678;21.3"""

    # Create a zip file in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
        zipf.writestr("data.csv", csv_content)
    zip_buffer.seek(0)

    # Mock the response
    mock_response = Mock()
    mock_response.content = zip_buffer.getvalue()
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response

    result = fetch_data("http://example.com/data.zip")

    assert not result.empty
    assert "Time" in result.columns
    assert "StationNumber" in result.columns
    assert "Temperature" in result.columns
    assert len(result) == 2


@patch("custom_components.hungaromet.weather_data.requests.get")
def test_fetch_data_http_error(mock_get):
    """Test fetch_data raises error on HTTP failure."""
    mock_response = Mock()
    mock_response.raise_for_status.side_effect = Exception("HTTP Error")
    mock_get.return_value = mock_response

    with pytest.raises(Exception, match="HTTP Error"):
        fetch_data("http://example.com/data.zip")


@patch("custom_components.hungaromet.weather_data.fetch_data")
def test_process_daily_data(mock_fetch):
    """Test process_daily_data processes data correctly."""
    mock_df = pd.DataFrame({
        "Time": [20240101, 20240101],
        "StationNumber": [1234, 5678],
        "StationName": ["Station A", "Station B"],
        "Latitude": [47.5, 47.6],
        "Longitude": [19.0, 19.1],
        "Elevation": [100, 110],
        "rau": [5.0, 7.0],
        "upe": [2.0, 3.0],
        "t": [20.0, 22.0],
        "tn": [15.0, 16.0],
        "tx": [25.0, 27.0],
        "sr": [800, 850],
        "et5": [10, 12],
        "et10": [11, 13],
        "et20": [12, 14],
        "et50": [13, 15],
        "et100": [14, 16],
        "tsn24": [5, 6],
    })
    mock_fetch.return_value = mock_df

    hass = Mock()
    hass.config.latitude = 47.5
    hass.config.longitude = 19.0

    result, station_info = process_daily_data(hass, distance_km=50.0)

    assert "time" in result
    assert result["time"] == "2024-01-01"
    assert "average_t" in result
    assert "average_rau" in result
    assert "average_upe" in result
    assert "average_water_balance" in result
    assert "average_sr_mj" in result
    assert len(station_info) > 0


@patch("custom_components.hungaromet.weather_data.fetch_data")
def test_process_hourly_data(mock_fetch):
    """Test process_hourly_data processes data correctly."""
    mock_df = pd.DataFrame({
        "Time": [202401011200, 202401011200],
        "StationNumber": [1234, 5678],
        "StationName": ["Station A", "Station B"],
        "Latitude": [47.5, 47.6],
        "Longitude": [19.0, 19.1],
        "Elevation": [100, 110],
        "r": [0.5, 1.0],
        "t": [20.0, 22.0],
        "ta": [19.0, 21.0],
        "tn": [15.0, 16.0],
        "tx": [25.0, 27.0],
        "u": [60, 65],
        "sg": [5, 6],
        "sr": [100, 110],
        "suv": [1, 2],
        "fs": [5.0, 6.0],
        "fsd": [180, 190],
        "fx": [8.0, 9.0],
        "fxd": [200, 210],
        "f": [4.0, 5.0],
        "fd": [170, 180],
        "we": [1, 1],
        "et5": [10, 12],
        "et10": [11, 13],
        "et20": [12, 14],
        "et50": [13, 15],
        "et100": [14, 16],
        "tsn": [5, 6],
        "tviz": [10000, 12000],
    })
    mock_fetch.return_value = mock_df

    hass = Mock()
    hass.config.latitude = 47.5
    hass.config.longitude = 19.0

    result, station_info = process_hourly_data(hass, distance_km=50.0)

    assert "time" in result
    assert "average_t" in result
    assert "average_r" in result
    assert "average_u" in result
    assert "average_sr_mj" in result
    assert "we" in result
    assert result["we"] == 1
    assert len(station_info) > 0


@patch("custom_components.hungaromet.weather_data.fetch_data")
def test_process_ten_minutes_data(mock_fetch):
    """Test process_ten_minutes_data processes data correctly."""
    mock_df = pd.DataFrame({
        "Time": [202401011230, 202401011230],
        "StationNumber": [1234, 5678],
        "StationName": ["Station A", "Station B"],
        "Latitude": [47.5, 47.6],
        "Longitude": [19.0, 19.1],
        "Elevation": [100, 110],
        "r": [0.5, 1.0],
        "t": [20.0, 22.0],
        "ta": [19.0, 21.0],
        "tn": [15.0, 16.0],
        "tx": [25.0, 27.0],
        "u": [60, 65],
        "sg": [5, 6],
        "sr": [50, 60],
        "suv": [1, 2],
        "fs": [5.0, 6.0],
        "fsd": [180, 190],
        "fx": [8.0, 9.0],
        "fxd": [200, 210],
        "et5": [10, 12],
        "et10": [11, 13],
        "et20": [12, 14],
        "et50": [13, 15],
        "et100": [14, 16],
        "tsn": [5, 6],
        "tviz": [10000, 12000],
    })
    mock_fetch.return_value = mock_df

    hass = Mock()
    hass.config.latitude = 47.5
    hass.config.longitude = 19.0

    result, station_info = process_ten_minutes_data(hass, distance_km=50.0)

    assert "time" in result
    assert "average_t" in result
    assert "average_r" in result
    assert "average_fs" in result
    assert "average_sr_mj" in result
    assert len(station_info) > 0


@patch("custom_components.hungaromet.weather_data.fetch_data")
def test_process_hourly_data_empty_we(mock_fetch):
    """Test process_hourly_data with empty 'we' column."""
    mock_df = pd.DataFrame({
        "Time": [202401011200],
        "StationNumber": [1234],
        "StationName": ["Station A"],
        "Latitude": [47.5],
        "Longitude": [19.0],
        "Elevation": [100],
        "r": [0.5],
        "t": [20.0],
        "ta": [19.0],
        "tn": [15.0],
        "tx": [25.0],
        "u": [60],
        "sg": [5],
        "sr": [100],
        "suv": [1],
        "fs": [5.0],
        "fsd": [180],
        "fx": [8.0],
        "fxd": [200],
        "f": [4.0],
        "fd": [170],
        "we": [pd.NA],  # Empty we value
        "et5": [10],
        "et10": [11],
        "et20": [12],
        "et50": [13],
        "et100": [14],
        "tsn": [5],
        "tviz": [10000],
    })
    mock_fetch.return_value = mock_df

    hass = Mock()
    hass.config.latitude = 47.5
    hass.config.longitude = 19.0

    result, _ = process_hourly_data(hass, distance_km=50.0)

    assert result["we"] is None


@patch("custom_components.hungaromet.weather_data.fetch_data")
def test_process_daily_data_water_balance_calculation(mock_fetch):
    """Test process_daily_data calculates water balance correctly."""
    mock_df = pd.DataFrame({
        "Time": [20240101],
        "StationNumber": [1234],
        "StationName": ["Station A"],
        "Latitude": [47.5],
        "Longitude": [19.0],
        "Elevation": [100],
        "rau": [10.0],
        "upe": [3.0],
        "t": [20.0],
        "tn": [15.0],
        "tx": [25.0],
        "sr": [800],
        "et5": [10],
        "et10": [11],
        "et20": [12],
        "et50": [13],
        "et100": [14],
        "tsn24": [5],
    })
    mock_fetch.return_value = mock_df

    hass = Mock()
    hass.config.latitude = 47.5
    hass.config.longitude = 19.0

    result, _ = process_daily_data(hass, distance_km=50.0)

    assert result["average_water_balance"] == pytest.approx(7.0, abs=0.1)
    assert result["average_sr_mj"] == pytest.approx(8.0, abs=0.1)


@patch("custom_components.hungaromet.weather_data.fetch_data")
def test_process_daily_data_water_balance_none_when_missing(mock_fetch):
    """Test process_daily_data water balance is None when data missing."""
    mock_df = pd.DataFrame({
        "Time": [20240101],
        "StationNumber": [1234],
        "StationName": ["Station A"],
        "Latitude": [47.5],
        "Longitude": [19.0],
        "Elevation": [100],
        "rau": [pd.NA],
        "upe": [3.0],
        "t": [20.0],
        "tn": [15.0],
        "tx": [25.0],
        "sr": [800],
        "et5": [10],
        "et10": [11],
        "et20": [12],
        "et50": [13],
        "et100": [14],
        "tsn24": [5],
    })
    mock_fetch.return_value = mock_df

    hass = Mock()
    hass.config.latitude = 47.5
    hass.config.longitude = 19.0

    result, _ = process_daily_data(hass, distance_km=50.0)

    assert result["average_water_balance"] is None
