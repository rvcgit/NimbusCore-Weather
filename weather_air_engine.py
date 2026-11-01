#!/usr/bin/env python3
# ---------------------------------------------------------------------------
# NIMBUSCORE UNIFIED WEATHER & AIR QUALITY ENGINE (v2.8) - PART 1 OF 3
# System initialization, global maps, and network geolocation routing.
# ---------------------------------------------------------------------------

import json
import math
import os
import platform
import tempfile
from datetime import datetime, timezone
from pathlib import Path
import requests

# ==================== GLOBAL USER SETTINGS ====================
AUTO_DETECT_LOCATION = True

# Overrides when AUTO_DETECT_LOCATION = False, or when IP geolocation fails.
MANUAL_LAT = None  # Edit with Specific Coordinate [ Latitude ]
MANUAL_LON = None  # Edit with Specific Coordinate [ Longitude ]

# Keep weather and air quality display synced to Indian Standard Time.
TIMEZONE = "Asia/Kolkata"
# ==============================================================

# ==================== CROSS-PLATFORM LOCATION DETECTION ====================

def get_coordinates():
    """Returns coordinates using explicit manual variables first when auto-detect is disabled."""
    if not AUTO_DETECT_LOCATION:
        if MANUAL_LAT is not None and MANUAL_LON is not None:
            if os.isatty(1):
                print(f"[LOCATION] Using manual override: latitude={MANUAL_LAT:.4f}, longitude={MANUAL_LON:.4f}")
            return float(MANUAL_LAT), float(MANUAL_LON)
        else:
            if os.isatty(1):
                print("[LOCATION] WARNING: AUTO_DETECT_LOCATION is False, but manual coordinates are None!")

    if os.isatty(1):
        print("Scanning public IP geolocation parameters...")
        
    try:
        response = requests.get("https://ipwho.is", timeout=5)
        response.raise_for_status()
        location = response.json()

        if location.get("success") is True:
            lat = float(location["latitude"])
            lon = float(location["longitude"])
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                if os.isatty(1):
                    print(f"Auto-detected location: latitude={lat:.4f}, longitude={lon:.4f}")
                return lat, lon
        raise ValueError("Geolocation service returned invalid coordinates.")
        
    except Exception as exc:
        if MANUAL_LAT is not None and MANUAL_LON is not None:
            if os.isatty(1):
                print(f"Geolocation failed. Falling back to manual coordinates: ({MANUAL_LAT}, {MANUAL_LON})")
            return float(MANUAL_LAT), float(MANUAL_LON)
        raise RuntimeError("Could not resolve coordinates. Configure manual fallbacks.") from exc

# ==================== RUNTIME MEMORY FILESYSTEM MAPPING ====================

SYSTEM_OS = platform.system().lower()
if "win" in SYSTEM_OS:
    CACHE_DIR = Path(os.environ.get("LOCALAPPDATA", r"C:\Users\User\AppData\Local")) / "Temp" / "WeatherCache"
else:
    CACHE_DIR = Path("/tmp")

CACHE_DIR.mkdir(parents=True, exist_ok=True)

# ==================== NERD FONT GLYPH DICTIONARIES ====================

ICONS = {
    "sun": "\uf185",           #  Bright Day Sun
    "moon": "\uf186",          #  Dusk Time Moon
    "partly_day": "\ue21d",    #  Clouds with Sun
    "partly_night": "\ue37e",  #  Clouds with Moon
    "cloud": "\ue312",         #  Dense Clouds
    "fog": "\ue30d",           #  Fog/Mist
    "drizzle": "\ue239",       #  Light Drizzle
    "rain": "\ue239",          #  Heavy Rain
    "snow": "\uf2dc",          #  Snow Fallback
    "storm": "\ue322",         #  Thunderstorm
    "wind": "\uf11e",          #  Wind Decorative Icon
}

WMO_TEXT_MAP = {
    0: "Clear Sky", 1: "Mainly Clear", 2: "Partly Cloudy", 3: "Overcast",
    45: "Foggy", 48: "Rime Fog", 51: "Light Drizzle", 53: "Moderate Drizzle",
    55: "Dense Drizzle", 56: "Light Freezing Drizzle", 57: "Dense Freezing Drizzle",
    61: "Slight Rain", 63: "Moderate Rain", 65: "Heavy Rain",
    66: "Light Freezing Rain", 67: "Heavy Freezing Rain",
    71: "Slight Snowfall", 73: "Moderate Snowfall", 75: "Heavy Snowfall", 77: "Snow Grains",
    80: "Slight Rain Showers", 81: "Moderate Rain Showers", 82: "Violent Rain Showers",
    85: "Slight Snow Showers", 86: "Heavy Snow Showers",
    95: "Thunderstorm", 96: "Thunderstorm with Slight Hail", 99: "Severe Thunderstorm"
}
# ---------------------------------------------------------------------------
# NIMBUSCORE UNIFIED WEATHER & AIR QUALITY ENGINE (v2.8) - PART 2 OF 3
# Mathematical algorithmic data handlers and parallel endpoints network core.
# ---------------------------------------------------------------------------

def weather_icon(code, is_day):
    """Maps WMO codes directly to Nerd Font glyph positions based on day/night states."""
    if code == 0: return ICONS["sun"] if is_day else ICONS["moon"]
    if code in (1, 2): return ICONS["partly_day"] if is_day else ICONS["partly_night"]
    if code == 3: return ICONS["cloud"]
    if code in (45, 48): return ICONS["fog"]
    if code in (51, 53, 55, 56, 57): return ICONS["drizzle"]
    if code in (61, 63, 65, 66, 67, 80, 81, 82): return ICONS["rain"]
    if code in (71, 73, 75, 77, 85, 86): return ICONS["snow"]
    if code in (95, 96, 99): return ICONS["storm"]
    return ICONS["cloud"]

def get_16_point_compass(degrees):
    """Translates raw degree updates into textual coordinates and direction characters."""
    degrees = (degrees % 360 + 360) % 360
    points = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    arrows = ["\u2193", "\u2199", "\u2199", "\u2199", "\u2190", "\u2196", "\u2196", "\u2196", "\u2191", "\u2197", "\u2197", "\u2197", "\u2192", "\u2198", "\u2198", "\u2198"]
    index = int((degrees + 11.25) / 22.5) % 16
    return points[index], arrows[index]

def moon_phase():
    """Computes exact lunar cycles relative to the synodic epoch base line date."""
    now = datetime.now(timezone.utc)
    new_moon = datetime(2000, 1, 6, 18, 14, tzinfo=timezone.utc)
    synodic_month = 29.530588853
    age = ((now - new_moon).total_seconds() / 86400) % synodic_month
    fraction = age / synodic_month
    illumination = (1 - math.cos(2 * math.pi * fraction)) / 2 * 100
    
    if fraction < 0.0625 or fraction >= 0.9375: m_glyph, name = "\ue3e3", "New Moon"
    elif fraction < 0.1875: m_glyph, name = "\ue3d5", "Waxing Crescent"
    elif fraction < 0.3125: m_glyph, name = "\ue3ce", "First Quarter"
    elif fraction < 0.4375: m_glyph, name = "\ue3ca", "Waxing Gibbous"
    elif fraction < 0.5625: m_glyph, name = "\ue3e3", "Full Moon"
    elif fraction < 0.6875: m_glyph, name = "\ue3c7", "Waning Gibbous"
    elif fraction < 0.8125: m_glyph, name = "\ue3c4", "Last Quarter"
    else: m_glyph, name = "\ue3c0", "Waning Crescent"
    return f"{m_glyph} {name} ({illumination:.0f}%)"

def atomic_write(filename, content):
    """Safely updates target disk files using temporary replacement buffers."""
    destination = CACHE_DIR / filename
    fd, temp_name = tempfile.mkstemp(dir=str(CACHE_DIR))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            file.write(str(content) + "\n")
        os.replace(temp_name, destination)
    finally:
        if os.path.exists(temp_name):
            try: os.unlink(temp_name)
            except OSError: pass

# ==================== CORE DATA INGESTION ENGINE ====================

def main():
    try:
        lat, lon = get_coordinates()
    except Exception as e:
        print(f"Location Error: {e}")
        return

    weather_url = "https://api.open-meteo.com/v1/forecast"
    weather_params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,apparent_temperature,wind_speed_10m,wind_direction_10m,is_day,weather_code",
        "hourly": "temperature_2m,weather_code",
        "daily": "temperature_2m_max,temperature_2m_min,weather_code",
        "timezone": TIMEZONE,
        "forecast_days": 5,
        "temperature_unit": "celsius",
        "wind_speed_unit": "ms",
    }

    aqi_url = "https://air-quality-api.open-meteo.com/v1/air-quality"
    aqi_params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "pm2_5,us_aqi",
        "timezone": TIMEZONE
    }

    try:
        w_res = requests.get(weather_url, params=weather_params, timeout=20)
        weather_data = w_res.json() if w_res.status_code == 200 else None
    except Exception as e:
        print(f"Weather API Network Failure: {e}")
        weather_data = None

    try:
        a_res = requests.get(aqi_url, params=aqi_params, timeout=20)
        aqi_data = a_res.json() if a_res.status_code == 200 else None
    except Exception as e:
        print(f"Air Quality API Network Failure: {e}")
        aqi_data = None

    if not weather_data or not aqi_data:
        print("[ERROR] Failed to fetch data from API endpoints.")
        _serve_cache_fallback()
        return
# ---------------------------------------------------------------------------
# NIMBUSCORE UNIFIED WEATHER & AIR QUALITY ENGINE (v2.8) - PART 3 OF 3
# Extraction logic mapping out all 10 cache tokens and generating CSV tables.
# ---------------------------------------------------------------------------

    # EXTRACT CORE RUNTIME DATA PAYLOAD VALUES
    current = weather_data.get("current", {})
    temp = current.get("temperature_2m", 0.0)
    apparent_temp = current.get("apparent_temperature", 0.0)
    wind_speed = current.get("wind_speed_10m", 0.0)
    wind_dir = current.get("wind_direction_10m", 0)
    is_day = current.get("is_day", 1)
    w_code = current.get("weather_code", 0)

    # FIXED: Safely extract only the current hour's integer out of the raw forecast list layout
    hourly_aqi = aqi_data.get("hourly", {})
    us_aqi_list = hourly_aqi.get("us_aqi", [0])
    
    if isinstance(us_aqi_list, list) and len(us_aqi_list) > 0:
        us_aqi = us_aqi_list[0]
    else:
        us_aqi = 0

    cond_text = WMO_TEXT_MAP.get(w_code, "Unknown Sky")
    icon = weather_icon(w_code, is_day)
    compass_pt, compass_arr = get_16_point_compass(wind_dir)
    m_phase = moon_phase()

    # ==================== DYNAMIC 5-DAY TOOLTIP GENERATOR ====================
    try:
        daily = weather_data.get("daily", {})
        forecast_lines = []
        
        for i in range(min(5, len(daily.get("time", [])))):
            raw_date = daily["time"][i]
            day_w_code = daily["weather_code"][i]
            max_t = daily["temperature_2m_max"][i]
            min_t = daily["temperature_2m_min"][i]
            
            date_obj = datetime.strptime(raw_date, "%Y-%m-%d")
            day_name = date_obj.strftime("%a")
            
            day_icon = weather_icon(day_w_code, is_day=1)
            day_text = WMO_TEXT_MAP.get(day_w_code, "Unknown Sky")
            
            line_str = f"{day_name}: {day_icon} {day_text} (Max: {max_t:.0f}\u00b0C / Min: {min_t:.0f}\u00b0C)"
            forecast_lines.append(line_str)
            
        extended_forecast_summary = "\n".join(forecast_lines)
    except Exception as e:
        extended_forecast_summary = cond_text

    # ==================== ATOMIC SYSTEM WRITE PIPELINE ====================
    try:
        compound_json = {
            "current": current,
            "weather_api": weather_data,
            "air_quality_api": aqi_data,
            "meta": {"processed_at": datetime.now(timezone.utc).isoformat(), "lat": lat, "lon": lon}
        }
        atomic_write("weather_api_cache.json", json.dumps(compound_json, indent=2))
        
        # Standalone Cache Nodes Writing Pipeline
        atomic_write("air_aqi_cache", str(us_aqi))
        atomic_write("weather_forecast_cache", extended_forecast_summary)
        atomic_write("weather_temp_cache", f"{temp:.1f}")
        atomic_write("weather_apparent_temp_cache", f"{apparent_temp:.1f}")
        atomic_write("weather_icon_cache", icon)
        atomic_write("weather_moon_phase_cache", m_phase)
        atomic_write("weather_wmo_code", str(w_code))
        atomic_write("weather_wind_speed_cache", f"{wind_speed:.1f}")
        atomic_write("weather_wind_direction_cache", f"{wind_dir}")
        atomic_write("weather_condition_cache", f"{icon} {cond_text}")

        if os.isatty(1):
            print(f"[SUCCESS] Refreshed all 10 cache blocks inside: {CACHE_DIR}")

    except Exception as e:
        print(f"Disk Write Configuration Interruption Error: {e}")

    # ==================== HISTORICAL CSV TABLES EXPORTERS ====================
    try:
        hourly = weather_data.get("hourly", {})
        hourly_lines = ["datetime,temperature_2m,weather_code"]
        for i in range(min(24, len(hourly.get("time", [])))):
            t_str = hourly["time"][i].replace("T", " ")
            hourly_lines.append(f"{t_str},{hourly['temperature_2m'][i]},{hourly['weather_code'][i]}")
        atomic_write("hourly_weather.csv", "\n".join(hourly_lines))
    except Exception:
        pass

    try:
        daily_data = weather_data.get("daily", {})
        daily_lines = ["date,weather_code,temperature_2m_max,temperature_2m_min"]
        for i in range(min(5, len(daily_data.get("time", [])))):
            daily_lines.append(f"{daily_data['time'][i]},{daily_data['weather_code'][i]},{daily_data['temperature_2m_max'][i]},{daily_data['temperature_2m_min'][i]}")
        atomic_write("daily_weather.csv", "\n".join(daily_lines))
    except Exception:
        pass

    # Process Terminal Standard Output Logging Layout
    try:
        aqi_val = int(us_aqi)
        if aqi_val <= 50: aqi_desc = "Good 🟢"
        elif aqi_val <= 100: aqi_desc = "Moderate 🟡"
        elif aqi_val <= 150: aqi_desc = "Unhealthy for Sensitive Groups 🟠"
        elif aqi_val <= 200: aqi_desc = "Unhealthy 🔴"
        elif aqi_val <= 300: aqi_desc = "Very Unhealthy 🟣"
        else: aqi_desc = "Hazardous 🟤"
    except Exception:
        aqi_desc = "Unknown"

    if os.isatty(1):
        print("\n================== CURRENT CLIMATE STATE ==================")
        print(f"Condition  : {icon}  {cond_text}")
        print(f"Temperature: {temp:.1f}\u00b0C (Feels Like: {apparent_temp:.1f}\u00b0C)")
        print(f"Wind State : {wind_speed:.1f} m/s {compass_arr} ({compass_pt})")
        print(f"Air Index  : AQI {us_aqi} ({aqi_desc})")
        print(f"Lunar Cycle: {m_phase}")
        print("===========================================================")

    waybar_payload = {
        "text": f"{icon} {temp:.1f}\u00b0C",
        "alt": cond_text,
        "tooltip": f"AQI: {us_aqi} ({aqi_desc})\nMoon: {m_phase}",
        "class": "weather",
        "percentage": int(us_aqi)
    }
    print(json.dumps(waybar_payload, ensure_ascii=False))


def _serve_cache_fallback():
    try:
        with open(CACHE_DIR / "weather_forecast_cache", "r", encoding="utf-8") as f: fallback_forecast = f.read().strip()
        cache_payload = {
            "text": "--\u00b0C",
            "tooltip": f"⚠️ Offline Mode\n\n{fallback_forecast}",
            "class": "weather-offline"
        }
        print(json.dumps(cache_payload, ensure_ascii=False))
    except Exception:
        print(json.dumps({"text": "\uf185 --\u00b0C", "tooltip": "Offline"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
