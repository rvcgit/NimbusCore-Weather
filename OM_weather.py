#!/usr/bin/env python3
# ---------------------------------------------------------------------------
# NIMBUSCORE WEATHER + AIR QUALITY ENGINE
# Cross-platform location detection, atomic cache writer and forecast exporter
#
# Weather: Open-Meteo Forecast API
# Air quality: Open-Meteo Air Quality API
# Geolocation: ipwho.is (IP-based approximate location)
#
# Dependencies:
#   python -m pip install requests
#
# Windows cache:
#   %LOCALAPPDATA%\Temp\WeatherCache
#
# Linux / macOS cache:
#   /tmp
# ---------------------------------------------------------------------------

from __future__ import annotations

import json
import math
import os
import platform
import tempfile
import time
from pathlib import Path
from typing import Any, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# ===========================================================================
# USER CONFIGURATION
# ===========================================================================

AUTO_DETECT_LOCATION = True

# Used when AUTO_DETECT_LOCATION = False, or when IP geolocation fails.
# These are the previous NimbusCore coordinates.
MANUAL_LAT = None # Edit with Specific Coordinate [ Latitude ]
MANUAL_LON = None # Edit with Specific Coordinate [ Longitude ]

# Open-Meteo forecast horizon.
FORECAST_DAYS = 5
PRECIPITATION_FORECAST_HOURS = 72

# Keep the weather display in Indian Standard Time.
TIMEZONE = "Asia/Kolkata"

# Network / retry settings.
REQUEST_TIMEOUT = 20
RETRIES = 5
BACKOFF_FACTOR = 0.4

WEATHER_API_URL = "https://api.open-meteo.com/v1/forecast"
AIR_QUALITY_API_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
GEOLOCATION_API_URL = "https://ipwho.is/"


# ===========================================================================
# OS-AWARE CACHE DIRECTORY
# ===========================================================================

def get_cache_directory() -> Path:
    system = platform.system().lower()

    if system == "windows":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            cache_dir = Path(local_app_data) / "Temp" / "WeatherCache"
        else:
            cache_dir = Path(tempfile.gettempdir()) / "WeatherCache"
    else:
        # Retains the established NimbusCore Linux / Unix cache convention.
        cache_dir = Path("/tmp")

    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


CACHE_DIR = get_cache_directory()


# ===========================================================================
# HTTP SESSION WITH RETRIES
# ===========================================================================

def create_session() -> requests.Session:
    retry_config = Retry(
        total=RETRIES,
        connect=RETRIES,
        read=RETRIES,
        status=RETRIES,
        backoff_factor=BACKOFF_FACTOR,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET"]),
        respect_retry_after_header=True,
    )

    adapter = HTTPAdapter(max_retries=retry_config)
    session = requests.Session()
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update({
        "User-Agent": "NimbusCore-Weather/2.0",
        "Accept": "application/json",
    })
    return session


SESSION = create_session()


# ===========================================================================
# ATOMIC CACHE WRITER
# ===========================================================================

def atomic_write(path: Path, content: str) -> None:
    """Write to a temporary file, then atomically replace the target."""
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=str(path.parent),
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temp_file:
            temp_file.write(content)
            temp_file.flush()
            os.fsync(temp_file.fileno())
            temp_path = Path(temp_file.name)

        os.replace(temp_path, path)
    finally:
        if temp_path is not None and temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass


def write_text_cache(filename: str, value: Any) -> None:
    if value is None:
        text_value = "--"
    elif isinstance(value, float):
        rounded = round(value, 1)
        text_value = str(int(rounded)) if rounded.is_integer() else str(rounded)
    else:
        text_value = str(value)

    atomic_write(CACHE_DIR / filename, text_value + "\n")


def write_json_cache(filename: str, data: dict) -> None:
    payload = json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False)
    atomic_write(CACHE_DIR / filename, payload + "\n")


def write_series_cache(filename: str, values: list) -> None:
    lines = []
    for value in values:
        if value is None:
            lines.append("--")
        elif isinstance(value, float):
            lines.append(str(round(value, 1)))
        else:
            lines.append(str(value))
    atomic_write(CACHE_DIR / filename, "\n".join(lines) + "\n")


# ===========================================================================
# LOCATION DETECTION
# ===========================================================================

def valid_coordinates(latitude: Any, longitude: Any) -> bool:
    try:
        lat = float(latitude)
        lon = float(longitude)
        return math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180
    except (TypeError, ValueError):
        return False


def detect_location() -> tuple[float, float, str]:
    if AUTO_DETECT_LOCATION:
        try:
            response = SESSION.get(GEOLOCATION_API_URL, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            data = response.json()

            if data.get("success") and valid_coordinates(data.get("latitude"), data.get("longitude")):
                lat = float(data["latitude"])
                lon = float(data["longitude"])
                city = data.get("city") or data.get("region") or data.get("country") or "Auto-detected"
                print(f"[LOCATION] Auto-detected: {city} ({lat:.4f}, {lon:.4f})")
                return lat, lon, "auto"
            print("[LOCATION] Geolocation service returned no usable coordinates.")
        except (requests.RequestException, ValueError, TypeError) as exc:
            print(f"[LOCATION] Auto-detection failed: {exc}")

    if valid_coordinates(MANUAL_LAT, MANUAL_LON):
        print(f"[LOCATION] Using manual coordinates ({MANUAL_LAT}, {MANUAL_LON})")
        return float(MANUAL_LAT), float(MANUAL_LON), "manual"

    raise RuntimeError(
        "No valid location available. Enable auto-detection or set MANUAL_LAT / MANUAL_LON."
    )


# ===========================================================================
# GENERAL HELPERS
# ===========================================================================

def number_or_none(value: Any) -> Optional[float]:
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def first_value(mapping: dict, key: str) -> Any:
    values = mapping.get(key)
    if isinstance(values, list):
        return values[0] if values else None
    return values


def round_value(value: Any, digits: int = 1) -> Optional[float]:
    number = number_or_none(value)
    return round(number, digits) if number is not None else None


def compass_direction(degrees: Any) -> str:
    value = number_or_none(degrees)
    if value is None:
        return "--"
    directions = [
        "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
        "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW",
    ]
    return directions[int((value + 11.25) / 22.5) % 16]


def wind_arrow(degrees: Any) -> str:
    """Arrow points toward the direction the wind is coming FROM, as in the
    previous NimbusCore compass convention."""
    value = number_or_none(degrees)
    if value is None:
        return "?"
    arrows = ["↓", "↙", "←", "↖", "↑", "↗", "→", "↘"]
    return arrows[int((value + 22.5) / 45.0) % 8]


def weather_icon(code: Any, is_day: Any) -> str:
    code_num = int(code) if number_or_none(code) is not None else -1
    day = int(is_day) == 1 if number_or_none(is_day) is not None else True

    if code_num == 0:
        return "" if day else ""
    if code_num in (1, 2):
        return "" if day else ""
    if code_num == 3:
        return ""
    if code_num in (45, 48):
        return ""
    if code_num in (51, 53, 55, 56, 57):
        return ""
    if code_num in (61, 63, 65, 66, 67, 80, 81, 82):
        return ""
    if code_num in (71, 73, 75, 77, 85, 86):
        return ""
    if code_num in (95, 96, 99):
        return ""
    return ""


def weather_condition(code: Any) -> str:
    code_num = int(code) if number_or_none(code) is not None else -1
    conditions = {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Fog",
        48: "Depositing rime fog",
        51: "Light drizzle",
        53: "Moderate drizzle",
        55: "Dense drizzle",
        56: "Freezing drizzle",
        57: "Dense freezing drizzle",
        61: "Slight rain",
        63: "Moderate rain",
        65: "Heavy rain",
        66: "Freezing rain",
        67: "Heavy freezing rain",
        71: "Slight snow",
        73: "Moderate snow",
        75: "Heavy snow",
        77: "Snow grains",
        80: "Rain showers",
        81: "Moderate rain showers",
        82: "Violent rain showers",
        85: "Snow showers",
        86: "Heavy snow showers",
        95: "Thunderstorm",
        96: "Thunderstorm with hail",
        99: "Heavy thunderstorm with hail",
    }
    return conditions.get(code_num, "Unknown")


def aqi_category(value: Any, standard: str) -> str:
    number = number_or_none(value)
    if number is None:
        return "--"

    if standard == "EU":
        if number <= 20:
            return "Good"
        if number <= 40:
            return "Fair"
        if number <= 60:
            return "Moderate"
        if number <= 80:
            return "Poor"
        if number <= 100:
            return "Very poor"
        return "Extremely poor"

    if number <= 50:
        return "Good"
    if number <= 100:
        return "Moderate"
    if number <= 150:
        return "Unhealthy-SG"
    if number <= 200:
        return "Unhealthy"
    if number <= 300:
        return "Very unhealthy"
    return "Hazardous"


# ===========================================================================
# API REQUESTS
# ===========================================================================

def get_json(url: str, params: dict) -> dict:
    response = SESSION.get(url, params=params, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    data = response.json()

    if not isinstance(data, dict) or data.get("error"):
        reason = data.get("reason", "Invalid API response") if isinstance(data, dict) else "Invalid JSON"
        raise RuntimeError(reason)

    return data


def fetch_weather(latitude: float, longitude: float) -> dict:
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": [
            "temperature_2m",
            "apparent_temperature",
            "is_day",
            "weather_code",
            "wind_speed_10m",
            "wind_direction_10m",
            "wind_gusts_10m",
            "relative_humidity_2m",
            "precipitation",
            "rain",
            "showers",
        ],
        "hourly": [
            "temperature_2m",
            "apparent_temperature",
            "relative_humidity_2m",
            "precipitation",
            "precipitation_probability",
            "rain",
            "showers",
            "weather_code",
            "visibility",
            "wind_speed_10m",
            "wind_direction_10m",
            "is_day",
            "sunshine_duration",
        ],
        "daily": [
            "temperature_2m_max",
            "temperature_2m_min",
            "apparent_temperature_max",
            "apparent_temperature_min",
            "weather_code",
            "precipitation_sum",
            "rain_sum",
            "showers_sum",
            "precipitation_hours",
            "precipitation_probability_max",
            "daylight_duration",
            "sunrise",
            "sunset",
            "sunshine_duration",
            "moon_phase",
            "moonrise",
            "moonset",
            "wind_speed_10m_max",
        ],
        "forecast_days": FORECAST_DAYS,
        "forecast_hours": PRECIPITATION_FORECAST_HOURS,
        "timezone": TIMEZONE,
        "wind_speed_unit": "ms",
        "temperature_unit": "celsius",
        "precipitation_unit": "mm",
    }
    return get_json(WEATHER_API_URL, params)


def fetch_air_quality(latitude: float, longitude: float) -> dict:
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": [
            "european_aqi",
            "us_aqi",
            "pm10",
            "pm2_5",
            "carbon_monoxide",
            "nitrogen_dioxide",
            "sulphur_dioxide",
            "ozone",
            "uv_index",
        ],
        "hourly": [
            "european_aqi",
            "us_aqi",
            "pm10",
            "pm2_5",
            "carbon_monoxide",
            "nitrogen_dioxide",
            "sulphur_dioxide",
            "ozone",
            "dust",
            "uv_index",
        ],
        "forecast_days": FORECAST_DAYS,
        "timezone": TIMEZONE,
    }
    return get_json(AIR_QUALITY_API_URL, params)


# ===========================================================================
# CACHE EXPORT
# ===========================================================================

def export_weather_caches(data: dict, latitude: float, longitude: float, location_mode: str) -> None:
    current = data.get("current") or {}
    hourly = data.get("hourly") or {}
    daily = data.get("daily") or {}

    temperature = round_value(current.get("temperature_2m"), 0)
    apparent = round_value(current.get("apparent_temperature"), 0)
    is_day = current.get("is_day")
    code = current.get("weather_code")
    wind_speed = round_value(current.get("wind_speed_10m"), 1)
    wind_direction = round_value(current.get("wind_direction_10m"), 0)
    wind_gust = round_value(current.get("wind_gusts_10m"), 1)
    humidity = round_value(current.get("relative_humidity_2m"), 0)
    precipitation = round_value(current.get("precipitation"), 1)
    rain = round_value(current.get("rain"), 1)
    showers = round_value(current.get("showers"), 1)

    # Legacy-compatible core cache names.
    write_text_cache("weather_temp_cache", temperature)
    write_text_cache("weather_apparent_temp_cache", apparent)
    write_text_cache("weather_icon_cache", weather_icon(code, is_day))
    write_text_cache("weather_condition_cache", weather_condition(code))
    write_text_cache("weather_time_status", "day" if str(is_day) == "1" else "night")
    write_text_cache("weather_wind_speed_cache", wind_speed)
    write_text_cache("weather_wind_direction_cache", wind_direction)
    write_text_cache("weather_wind_compass_cache", compass_direction(wind_direction))
    write_text_cache("weather_wind_arrow_cache", wind_arrow(wind_direction))
    write_text_cache("weather_wind_gust_cache", wind_gust)
    write_text_cache("weather_humidity_cache", humidity)

    # Current precipitation.
    write_text_cache("weather_precipitation_cache", precipitation)
    write_text_cache("weather_rain_cache", rain)
    write_text_cache("weather_showers_cache", showers)

    # Current local time / location metadata.
    write_text_cache("weather_current_time_cache", current.get("time"))
    write_text_cache("weather_latitude_cache", latitude)
    write_text_cache("weather_longitude_cache", longitude)
    write_text_cache("weather_location_mode_cache", location_mode)

    # Daily lunar / solar data: today's first forecast day.
    write_text_cache("weather_moon_phase_cache", round_value(first_value(daily, "moon_phase"), 3))
    write_text_cache("weather_sunrise_cache", first_value(daily, "sunrise"))
    write_text_cache("weather_sunset_cache", first_value(daily, "sunset"))
    write_text_cache("weather_daylight_duration_cache", round_value(first_value(daily, "daylight_duration"), 0))
    write_text_cache("weather_moonrise_cache", first_value(daily, "moonrise"))
    write_text_cache("weather_moonset_cache", first_value(daily, "moonset"))

    # Keep the hourly timestamps alongside the 72-hour value series so that
    # Rainmeter or another panel can align forecast values with local time.
    write_series_cache("weather_hourly_time_cache", hourly.get("time", [])[:PRECIPITATION_FORECAST_HOURS])

    # Hourly forecast cache files. Each file contains one value per hour.
    hourly_cache_map = {
        "weather_temperature_forecast_cache": "temperature_2m",
        "weather_apparent_temperature_forecast_cache": "apparent_temperature",
        "weather_precipitation_forecast_cache": "precipitation",
        "weather_precipitation_probability_cache": "precipitation_probability",
        "weather_rain_forecast_cache": "rain",
        "weather_showers_forecast_cache": "showers",
        "weather_humidity_forecast_cache": "relative_humidity_2m",
        "weather_visibility_forecast_cache": "visibility",
        "weather_wind_forecast_cache": "wind_speed_10m",
        "weather_code_forecast_cache": "weather_code",
        "weather_is_day_forecast_cache": "is_day",
    }
    for filename, key in hourly_cache_map.items():
        write_series_cache(filename, (hourly.get(key) or [])[:PRECIPITATION_FORECAST_HOURS])

    # Daily forecast cache files.
    daily_cache_map = {
        "weather_daily_temp_max_cache": "temperature_2m_max",
        "weather_daily_temp_min_cache": "temperature_2m_min",
        "weather_daily_apparent_temp_max_cache": "apparent_temperature_max",
        "weather_daily_apparent_temp_min_cache": "apparent_temperature_min",
        "weather_precipitation_daily_cache": "precipitation_sum",
        "weather_rain_daily_cache": "rain_sum",
        "weather_showers_daily_cache": "showers_sum",
        "weather_precipitation_hours_cache": "precipitation_hours",
        "weather_precipitation_probability_daily_cache": "precipitation_probability_max",
        "weather_daily_wind_max_cache": "wind_speed_10m_max",
        "weather_daily_code_cache": "weather_code",
    }
    for filename, key in daily_cache_map.items():
        write_series_cache(filename, daily.get(key) or [])

    # Full raw response for inspection / future panel development.
    write_json_cache("weather_api_cache.json", data)


def export_air_quality_caches(data: dict) -> None:
    current = data.get("current") or {}
    hourly = data.get("hourly") or {}

    eu_aqi = current.get("european_aqi")
    us_aqi = current.get("us_aqi")

    write_text_cache("weather_aqi_cache", eu_aqi)
    write_text_cache("weather_aqi_category_cache", aqi_category(eu_aqi, "EU"))
    write_text_cache("weather_us_aqi_cache", us_aqi)
    write_text_cache("weather_us_aqi_category_cache", aqi_category(us_aqi, "US"))

    pollutant_map = {
        "weather_pm2_5_cache": "pm2_5",
        "weather_pm10_cache": "pm10",
        "weather_carbon_monoxide_cache": "carbon_monoxide",
        "weather_nitrogen_dioxide_cache": "nitrogen_dioxide",
        "weather_sulphur_dioxide_cache": "sulphur_dioxide",
        "weather_ozone_cache": "ozone",
        "weather_uv_index_cache": "uv_index",
    }
    for filename, key in pollutant_map.items():
        write_text_cache(filename, round_value(current.get(key), 1))

    hourly_aqi_map = {
        "weather_aqi_forecast_cache": "european_aqi",
        "weather_us_aqi_forecast_cache": "us_aqi",
        "weather_pm2_5_forecast_cache": "pm2_5",
        "weather_pm10_forecast_cache": "pm10",
        "weather_ozone_forecast_cache": "ozone",
        "weather_nitrogen_dioxide_forecast_cache": "nitrogen_dioxide",
    }
    for filename, key in hourly_aqi_map.items():
        write_series_cache(filename, (hourly.get(key) or [])[:PRECIPITATION_FORECAST_HOURS])

    write_text_cache("weather_aqi_time_cache", current.get("time"))
    write_json_cache("weather_air_quality_cache.json", data)


# ===========================================================================
# MAIN
# ===========================================================================

def main() -> int:
    print("=" * 68)
    print(" NIMBUSCORE WEATHER + AIR QUALITY ENGINE")
    print("=" * 68)
    print(f"[SYSTEM] {platform.system()} | Cache: {CACHE_DIR}")

    latitude, longitude, location_mode = detect_location()

    weather_data = None
    air_quality_data = None
    errors = []

    try:
        print("[WEATHER] Requesting forecast data...")
        weather_data = fetch_weather(latitude, longitude)
        export_weather_caches(weather_data, latitude, longitude, location_mode)
        print("[WEATHER] Data retrieved and caches updated.")
    except (requests.RequestException, ValueError, RuntimeError, KeyError) as exc:
        errors.append(f"Weather API: {exc}")
        print(f"[ERROR] Weather request/export failed: {exc}")

    try:
        print("[AIR QUALITY] Requesting AQI and pollutant data...")
        air_quality_data = fetch_air_quality(latitude, longitude)
        export_air_quality_caches(air_quality_data)
        print("[AIR QUALITY] Data retrieved and caches updated.")
    except (requests.RequestException, ValueError, RuntimeError, KeyError) as exc:
        errors.append(f"Air Quality API: {exc}")
        print(f"[ERROR] Air-quality request/export failed: {exc}")

    if weather_data:
        current = weather_data.get("current") or {}
        print(
            f"[CURRENT] {current.get('temperature_2m', '--')}°C "
            f"(feels like {current.get('apparent_temperature', '--')}°C) | "
            f"Wind {current.get('wind_speed_10m', '--')} m/s | "
            f"Precipitation {current.get('precipitation', '--')} mm"
        )

    if air_quality_data:
        current = air_quality_data.get("current") or {}
        print(
            f"[AQI] European {current.get('european_aqi', '--')} "
            f"({aqi_category(current.get('european_aqi'), 'EU')}) | "
            f"US {current.get('us_aqi', '--')} "
            f"({aqi_category(current.get('us_aqi'), 'US')}) | "
            f"PM2.5 {current.get('pm2_5', '--')} µg/m³"
        )

    if errors:
        print("[DONE] Completed with errors. Failed API caches were left untouched.")
        for error in errors:
            print(f"       - {error}")
        return 1

    print(f"[DONE] All cache files updated successfully in: {CACHE_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
