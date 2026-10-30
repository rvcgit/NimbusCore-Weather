#!/usr/bin/env python3
# ---------------------------------------------------------------------------
# NIMBUSCORE UNIFIED WEATHER & AIR QUALITY ENGINE (v2.7) - PART 1/7
# Core imports, cross-platform location overrides, and timezone declarations.
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
    """Returns coordinates using explicit manual variables first, falling back to public IP."""
    if not AUTO_DETECT_LOCATION and MANUAL_LAT is not None and MANUAL_LON is not None:
        if os.isatty(1):
            print(f"Prioritizing manual override coordinates: latitude={MANUAL_LAT:.4f}, longitude={MANUAL_LON:.4f}")
        return float(MANUAL_LAT), float(MANUAL_LON)

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

# Detect Operating System layout and resolve volatile target directories dynamically
SYSTEM_OS = platform.system().lower()
if "win" in SYSTEM_OS:
    CACHE_DIR = Path(os.environ.get("LOCALAPPDATA", r"C:\Users\User\AppData\Local")) / "Temp" / "WeatherCache"
else:
    CACHE_DIR = Path("/tmp")

CACHE_DIR.mkdir(parents=True, exist_ok=True)
# ==================== NERD FONT GLYPH DICTIONARIES ====================

# Explicit Character Node Glyphs bound to escaped hex addresses
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
    "wind": "\uf11e",          #  Wind Decorative Icon   # alternate "\uEF16",  ##   Wind Decoration
}

# Standard WMO Weather Code Mappings to English Text Phrasing
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
# ==================== DATA MATHEMATICS & ALGORITHMIC HELPERS ====================

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

def calculate_us_aqi(pm25):
    """Implements standard US EPA piece-wise scaling curves for particle matter."""
    if pm25 is None or pm25 < 0: return 0
    breakpoints = [
        (0.0, 12.0, 0, 50), (12.1, 35.4, 51, 100), (35.5, 55.4, 101, 150),
        (55.5, 150.4, 151, 200), (150.5, 250.4, 201, 300), (250.5, 500.4, 301, 500)
    ]
    for low_c, high_c, low_i, high_i in breakpoints:
        if low_c <= pm25 <= high_c:
            return int(((high_i - low_i) / (high_c - low_c)) * (pm25 - low_c) + low_i)
    return 500

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
# ==================== CLIMATE CALCULATION ENGINES ====================

def weather_icon(code, is_day):
    """Maps WMO weather codes to specific day/night character glyph definitions."""
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
    """Calculates wind heading directions and structural compass tracking arrows."""
    degrees = (degrees % 360 + 360) % 360
    points = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    arrows = ["\u2193", "\u2199", "\u2199", "\u2199", "\u2190", "\u2196", "\u2196", "\u2196", "\u2191", "\u2197", "\u2197", "\u2197", "\u2192", "\u2198", "\u2198", "\u2198"]
    index = int((degrees + 11.25) / 22.5) % 16
    return points[index], arrows[index]


def calculate_us_aqi(pm25):
    """Converts raw PM2.5 particle values into a standardized US EPA AQI integer."""
    if pm25 is None or pm25 < 0: return 0
    breakpoints = [
        (0.0, 12.0, 0, 50), (12.1, 35.4, 51, 100), (35.5, 55.4, 101, 150),
        (55.5, 150.4, 151, 200), (150.5, 250.4, 201, 300), (250.5, 500.4, 301, 500)
    ]
    for low_c, high_c, low_i, high_i in breakpoints:
        if low_c <= pm25 <= high_c:
            return int(((high_i - low_i) / (high_c - low_c)) * (pm25 - low_c) + low_i)
    return 500


def moon_phase():
    """Tracks historical lunar cycles to compute the active glyph name and percent lit."""
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

# ==================== ATOMIC SYSTEM WRITE PIPELINE ====================

def atomic_write(filename, content):
    """Safely updates target disk files using temporary replacement buffers."""
    destination = CACHE_DIR / filename
    fd, temp_name = tempfile.mkstemp(dir=str(CACHE_DIR))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            file.write(content + "\n")
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

    # 1. STRUCTURING DYNAMIC CLIMATE API QUERY SCHEMES
    weather_url = "https://api.open-meteo.com/v1/forecast"
    weather_params = {
        "latitude": lat,
        "longitude": lon,
        "current": ["temperature_2m", "apparent_temperature", "wind_speed_10m", "wind_direction_10m", "is_day", "weather_code"],
        "hourly": ["temperature_2m", "weather_code"],
        "daily": ["temperature_2m_max", "temperature_2m_min", "weather_code"],
        "timezone": TIMEZONE,
        "forecast_days": 5,
        "temperature_unit": "celsius",
        "wind_speed_unit": "ms",
    }

    aqi_url = "https://air-quality-api.open-meteo.com/v1/air-quality"
    aqi_params = {
        "latitude": lat,
        "longitude": lon,
        # CRITICAL FIX: Air quality parameters must be requested in the "hourly" parameter list
        "hourly": ["pm2_5", "us_aqi"],
        "timezone": TIMEZONE
    }

    # ==================== PART 5: DATA INGESTION ENGINE ====================
    # Executing Parallel Endpoint Handshakes safely with try/except blocks
    try:
        w_res = requests.get(weather_url, params=weather_params, timeout=20)
        if w_res.status_code == 200:
            weather_data = w_res.json()
        else:
            print(f"Weather API Fetch Failure: Status {w_res.status_code}")
            weather_data = None
    except Exception as e:
        print(f"Weather API Network Failure: {e}")
        weather_data = None

    try:
        a_res = requests.get(aqi_url, params=aqi_params, timeout=20)
        if a_res.status_code == 200:
            aqi_data = a_res.json()
        else:
            print(f"Air Quality API Fetch Failure: Status {a_res.status_code}")
            aqi_data = None
    except Exception as e:
        print(f"Air Quality API Network Failure: {e}")
        aqi_data = None

    m_phase = moon_phase()

    # ==================== PART 6: VALUE EXTRACTION & PARSING ====================
    if weather_data is None or "current" not in weather_data:
        raise RuntimeError("Weather payload is invalid or unavailable.")

    current_w = weather_data.get("current", {})
    temp = current_w.get("temperature_2m", 0.0)
    apparent_temp = current_w.get("apparent_temperature", 0.0)
    wmo_code = current_w.get("weather_code", 0)
    is_day = int(current_w.get("is_day", 1))
    wind_speed = current_w.get("wind_speed_10m", 0.0)
    wind_deg = current_w.get("wind_direction_10m", 0)
    
    aqi_hourly = aqi_data.get("hourly", {}) if aqi_data else {}
    pm25_list = aqi_hourly.get("pm2_5", [])
    server_aqi_list = aqi_hourly.get("us_aqi", [])
    
    pm25 = pm25_list[0] if len(pm25_list) > 0 else None
    server_aqi = server_aqi_list[0] if len(server_aqi_list) > 0 else None
    
    if server_aqi is not None:
        us_aqi = int(server_aqi)
    elif pm25 is not None:
        us_aqi = calculate_us_aqi(pm25)
    else:
        us_aqi = "--"

    compass_pt, compass_arr = get_16_point_compass(wind_deg)
    icon = weather_icon(wmo_code, is_day == 1)
    cond_text = WMO_TEXT_MAP.get(wmo_code, "Unknown")

    atomic_write("weather_icon_cache", icon)
    atomic_write("weather_temp_cache", f"{temp:.1f}\u00b0C")
    atomic_write("weather_temp_apparent_cache", f"{apparent_temp:.1f}\u00b0C")
    atomic_write("weather_code_cache", str(wmo_code))
    atomic_write("weather_condition_cache", cond_text)
    atomic_write("weather_moon_phase_cache", m_phase)
    atomic_write("weather_wind_speed_cache", f"{ICONS['wind']} {wind_speed:.1f} m/s {compass_arr} ({compass_pt})")
    atomic_write("weather_wind_direction_cache", f"{compass_arr} ({compass_pt})")
    atomic_write("weather_time_status", "day" if is_day == 1 else "night")
    atomic_write("air_aqi_cache", str(us_aqi))

    try:
        daily_data = weather_data.get("daily", {})
        times = daily_data.get("time", ["--", "--"])
        max_temps = daily_data.get("temperature_2m_max", [0.0, 0.0])
        min_temps = daily_data.get("temperature_2m_min", [0.0, 0.0])
        codes = daily_data.get("weather_code", [0, 0])

        d1_date = times[0] if len(times) > 0 else "--"
        d2_date = times[1] if len(times) > 1 else "--"
        d1_max = max_temps[0] if len(max_temps) > 0 else 0.0
        d2_max = max_temps[1] if len(max_temps) > 1 else 0.0
        d1_min = min_temps[0] if len(min_temps) > 0 else 0.0
        d2_min = min_temps[1] if len(min_temps) > 1 else 0.0
        d1_code = codes[0] if len(codes) > 0 else 0
        d2_code = codes[1] if len(codes) > 1 else 0
        
        d1_txt = WMO_TEXT_MAP.get(int(d1_code), "Unknown")
        d2_txt = WMO_TEXT_MAP.get(int(d2_code), "Unknown")
        
        forecast_text = (
            "📅 {} (Today)\n"
            "✨ Condition: {}\n"
            "🔺 Max: {}°C\n"
            "🔻 Min: {}°C\n\n"
            "📅 {} (Tomorrow)\n"
            "✨ Condition: {}\n"
            "🔺 Max: {}°C\n"
            "🔻 Min: {}°C"
        ).format(
            str(d1_date), str(d1_txt), round(d1_max), round(d1_min),
            str(d2_date), str(d2_txt), round(d2_max), round(d2_min)
        )
        atomic_write("weather_forecast_cache", forecast_text)
    except Exception:
        forecast_text = "Forecast Details Unavailable"
        atomic_write("weather_forecast_cache", forecast_text)

    # ==================== PART 7: OUTPUT & WAYBAR GENERATOR ====================
    try:
        compound_json = {
            "weather_api": weather_data,
            "air_quality_api": aqi_data,
            "meta": {"processed_at": datetime.now(timezone.utc).isoformat(), "lat": lat, "lon": lon}
        }
        atomic_write("weather_api_cache.json", json.dumps(compound_json, indent=2))
    except Exception:
        pass

    try:
        hourly = weather_data.get("hourly", {})
        with open(CACHE_DIR / "hourly_weather.csv", "w", encoding="utf-8") as f:
            f.write("datetime,temperature_2m,weather_code\n")
            for i in range(min(24, len(hourly.get("time", [])))):
                t_str = hourly["time"][i].replace("T", " ")
                f.write(f"{t_str},{hourly['temperature_2m'][i]},{hourly['weather_code'][i]}\n")
    except Exception:
        pass

    # 1. RESOLVE THE AIR QUALITY INTENSITY PHRASE DIRECTLY IN-SCRIPT
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
        print(f"Air Index  : US AQI {us_aqi} ({aqi_desc})")
        print(f"Lunar Cycle: {m_phase}")
        print("===========================================================")

    # 2. INJECT THE INTENSITY INTO THE HOVER TOOLTIP MENU
    tooltip_top = (
        "Condition: {} {}\n"
        "Temperature: {:.1f}\u00b0C\n"
        "Wind Speed: {:.1f} m/s {} ({})\n"
        "Air Quality: US AQI {} ({})\n"
        "Lunar Cycle: {}"
    ).format(icon, cond_text, temp, wind_speed, compass_arr, compass_pt, us_aqi, aqi_desc, m_phase)

    full_tooltip = "{}\n\n{}".format(tooltip_top, forecast_text)

    waybar_payload = {
        "text": f"{icon} {temp:.1f}\u00b0C",
        "alt": cond_text,
        "tooltip": full_tooltip,
        "class": "weather",
        "percentage": int(us_aqi) if str(us_aqi).isdigit() else 0
    }
    print(json.dumps(waybar_payload, ensure_ascii=False))


def _serve_cache_fallback():
    """Reads disk caches to output clean data strings to stdout for Waybar."""
    try:
        with open(CACHE_DIR / "weather_icon_cache", "r", encoding="utf-8") as f: fallback_icon = f.read().strip()
        with open(CACHE_DIR / "weather_temp_cache", "r", encoding="utf-8") as f: fallback_temp = f.read().strip()
        with open(CACHE_DIR / "weather_forecast_cache", "r", encoding="utf-8") as f: fallback_forecast = f.read().strip()
        
        cache_payload = {
            "text": f"{fallback_icon} {fallback_temp}",
            "tooltip": f"⚠️ Running in Offline Mode\n\n{fallback_forecast}",
            "class": "weather-offline"
        }
        print(json.dumps(cache_payload, ensure_ascii=False))
    except Exception:
        print(json.dumps({"text": "\uf185 --\u00b0C", "tooltip": "Offline"}, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        _serve_cache_fallback()
