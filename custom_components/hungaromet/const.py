DOMAIN = "hungaromet"
DEFAULT_NAME = "HungaroMet"
CONF_DISTANCE_KM = "distance_km"
DEFAULT_DISTANCE_KM = 20

URL_PROTOCOL = "https://"
URL_BASE = "odp.met.hu"

URL_SYNOPTIC = f"{URL_PROTOCOL}{URL_BASE}/weather/weather_reports/synoptic/hungary"
URL_RADAR = f"{URL_PROTOCOL}{URL_BASE}/weather/radar"

URL_DAILY = f"{URL_SYNOPTIC}/daily/csv/HABP_1D_LATEST.csv.zip"
URL_HOURLY = f"{URL_SYNOPTIC}/hourly/csv/HABP_1H_SYNOP_LATEST.csv.zip"
URL_TEN_MINUTES = f"{URL_SYNOPTIC}/10_minutes/csv/HABP_10M_SYNOP_LATEST.csv.zip"
RADAR_BASE_URL = f"{URL_RADAR}/composite/png/refl2D_pscappi/"
