#!/usr/bin/env python3
# ------------------------------------------------------------------
# CROSS-PLATFORM NATIVE ATOMIC WEATHER ENGINE & LUNAR DYNAMICS
# ------------------------------------------------------------------
import requests
import json
import math
import os
import tempfile
import platform
from datetime import datetime, timezone
from pathlib import Path

# ==================== CROSS-PLATFORM CONFIGURATION ====================================
# Optional "manual overrides" for location profiling.
# If these coordinates are explicitly configured, the script bypasses auto-detection.
# To use auto-detection, set both variables back to 'None'.
MANUAL_LAT = None # IF SPECIFIC LON NEEDED, EDIT HERE WITH YOUR LATITUDE

MANUAL_LON = None # IF SPECIFIC LON NEEDED, EDIT HERE WITH YOUR LONGITUDE [ "-" prefix needed for W lon ]
# =====================================================================================

def get_coordinates():
    """Returns coordinates using explicit manual variables first, falling back to public IP."""
    # 1. 🌟 CORE STRATEGY: If manual coordinates are provided, prioritize them immediately
    if MANUAL_LAT is not None and MANUAL_LON is not None:
        print(f"Prioritizing manual override coordinates: latitude={MANUAL_LAT:.4f}, longitude={MANUAL_LON:.4f}")
        return float(MANUAL_LAT), float(MANUAL_LON)

    # 2. Fallback to IP Network Geolocation scanning if manual inputs are blank
    print("No manual override detected. Scanning public IP geolocation parameters...")
    try:
        response = requests.get("https://ipwho.is", timeout=5)
        response.raise_for_status()
        location = response.json()

        if location.get("success") is True:
            lat = float(location["latitude"])
            lon = float(location["longitude"])

            if -90 <= lat <= 90 and -180 <= lon <= 180:
                print(f"Auto-detected location: latitude={lat:.4f}, longitude={lon:.4f}")
                return lat, lon

        raise ValueError("Geolocation service returned invalid coordinates.")

    except Exception as exc:
        raise RuntimeError(
            "Could not resolve coordinates. Configure MANUAL_LAT and MANUAL_LON variables."
        ) from exc
                     
API_URL = "https://api.open-meteo.com/v1/forecast"

# Detect Operating System and set CACHE_DIR dynamically
SYSTEM_OS = platform.system().lower()

if "win" in SYSTEM_OS:
    CACHE_DIR = Path(os.environ.get("LOCALAPPDATA", r"C:\Users\User\AppData\Local")) / "Temp" / "WeatherCache"
else:
    CACHE_DIR = Path("/tmp")

CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Explicit Nerd Font Character Glyph Nodes
ICONS = {
    "sun": "",           # Bright Day Sun
    "moon": "",          # Dusk Time Moon
    "partly_day": "",    # Clouds with Sun
    "partly_night": "",  # Clouds with Moon
    "cloud": "",         # Dense Clouds
    "fog": "",           # Fog/Mist
    "drizzle": "",       # Light Drizzle
    "rain": "",          # Heavy Rain
    "snow": "",          # Snow Fallback
    "storm": "",         # Thunderstorm
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

def weather_icon(code, is_day):
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
    degrees = (degrees % 360 + 360) % 360
    points = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    arrows = ["↓", "↙", "↙", "↙", "←", "↖", "↖", "↖", "↑", "↗", "↗", "↗", "→", "↘", "↘", "↘"]
    index = int((degrees + 11.25) / 22.5) % 16
    return points[index], arrows[index]

def moon_phase():
    now = datetime.now(timezone.utc)
    new_moon = datetime(2000, 1, 6, 18, 14, tzinfo=timezone.utc)
    synodic_month = 29.530588853
    age = ((now - new_moon).total_seconds() / 86400) % synodic_month
    fraction = age / synodic_month
    illumination = (1 - math.cos(2 * math.pi * fraction)) / 2 * 100
    if fraction < 0.0625 or fraction >= 0.9375: m_glyph, name = "", "New Moon"
    elif fraction < 0.1875: m_glyph, name = "", "Waxing Crescent"
    elif fraction < 0.3125: m_glyph, name = "", "First Quarter"
    elif fraction < 0.4375: m_glyph, name = "", "Waxing Gibbous"
    elif fraction < 0.5625: m_glyph, name = "", "Full Moon"
    elif fraction < 0.6875: m_glyph, name = "", "Waning Gibbous"
    elif fraction < 0.8125: m_glyph, name = "", "Last Quarter"
    else: m_glyph, name = "", "Waning Crescent"
    return f"{m_glyph} {name} ({illumination:.0f}%)"

def atomic_write(filename, content):
    destination = CACHE_DIR / filename
    fd, temp_name = tempfile.mkstemp(dir=str(CACHE_DIR))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file: file.write(content + "\n")
        os.replace(temp_name, destination)
    finally:
        if os.path.exists(temp_name):
            try: os.unlink(temp_name)
            except OSError: pass

def main():
    try:
        lat, lon = get_coordinates()
    except Exception as e:
        print(f"Location Error: {e}")
        return

    # Using clean lists without .join strings. 
    # Python requests safely maps multiple parameters matching Open-Meteo's strict array expectations.
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": ["temperature_2m", "wind_speed_10m", "wind_direction_10m", "is_day", "weather_code"],
        "hourly": ["temperature_2m", "weather_code"],
        "daily": ["temperature_2m_max", "temperature_2m_min", "weather_code"],
        "timezone": "auto",
        "forecast_days": 5,
        "temperature_unit": "celsius",
        "wind_speed_unit": "ms",
    }    
    
    try:
        response = requests.get(API_URL, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"API Fetch Failure: {e}")
        data = None

    m_phase = moon_phase()

    if data is None:
        # Offline Fallback Core Writes
        atomic_write("weather_icon_cache", "")
        atomic_write("weather_temp_cache", "--°C")
        atomic_write("weather_condition_cache", "Unknown")
        atomic_write("weather_moon_phase_cache", m_phase)
        atomic_write("weather_wind_speed_cache", "0.0 m/s")
        atomic_write("weather_time_status", "day")
        atomic_write("weather_code_cache", "0")
        return

    # 1. PROCESS CURRENT DATA
    current = data.get("current", {})
    temp = current.get("temperature_2m", 0.0)
    wmo_code = current.get("weather_code", 0)
    is_day = int(current.get("is_day", 1))
    wind_speed = current.get("wind_speed_10m", 0.0)
    wind_deg = current.get("wind_direction_10m", 0)
    
    compass_pt, compass_arr = get_16_point_compass(wind_deg)
    icon = weather_icon(wmo_code, is_day == 1)
    cond_text = WMO_TEXT_MAP.get(wmo_code, "Unknown")
    
    # 2. WRITE SYSTEM LEVEL CACHES FOR STRIP PANELS
    atomic_write("weather_icon_cache", icon)
    atomic_write("weather_temp_cache", f"{temp:.1f}°C")
    atomic_write("weather_code_cache", str(wmo_code))
    atomic_write("weather_condition_cache", cond_text)
    atomic_write("weather_moon_phase_cache", m_phase)
    atomic_write("weather_wind_speed_cache", f"{wind_speed:.1f} m/s {compass_arr} ({compass_pt})")
    atomic_write("weather_time_status", "day" if is_day == 1 else "night")

    # 3. EXPORT INDIVIDUAL CLEAN CSV PARSED DATA SHEETS FOR UNIFIED POPUPS
    try:
        # Build Hourly CSV
        hourly = data.get("hourly", {})
        with open(CACHE_DIR / "hourly_weather.csv", "w", encoding="utf-8") as f:
            f.write("datetime,temperature_2m,weather_code\n")
            for i in range(min(24, len(hourly.get("time", [])))):
                t_str = hourly["time"][i].replace("T", " ")
                f.write(f"{t_str},{hourly['temperature_2m'][i]},{hourly['weather_code'][i]}\n")

        # Build Daily CSV
        daily = data.get("daily", {})
        with open(CACHE_DIR / "daily_weather.csv", "w", encoding="utf-8") as f:
            f.write("date,weather_code,temperature_2m_max,temperature_2m_min\n")
            for i in range(min(5, len(daily.get("time", [])))):
                f.write(f"{daily['time'][i]},{daily['weather_code'][i]},{daily['temperature_2m_max'][i]},{daily['temperature_2m_min'][i]}\n")
    except Exception as csv_err:
        print(f"Failed to generate CSV templates: {csv_err}")

    # 4. 🌟 PRINT LIVE RESULTS STRAIGHT TO THE RUNNING TERMINAL EMULATOR
    print("\n================== CURRENT WEATHER STATE ==================")
    print(f"Condition  : {icon}  {cond_text}")
    print(f"Temperature: {'🔥'}{temp:.1f}°C")
    print(f"Wind Speed : {' '}{wind_speed:.1f} m/s {compass_arr} ({compass_pt})")
    print(f"Time Mode  : {'☀️ DAYTIME' if is_day == 1 else '🌙 NIGHTTIME'}")
    print(f"Lunar Cycle: {m_phase}")
    print("===========================================================")
    
    # 5. GENERATE & PRINT NATIVE WAYBAR FORMAT JSON STRINGS
    waybar_output = {
        "text": f"{icon}  {temp:.1f}°C",
        "tooltip": f"Condition: {cond_text}\nWind: {wind_speed:.1f} m/s {compass_pt}\nLunar: {m_phase}",
        "class": "weather",
        "percentage": 0
    }
    print(f"\nWaybar Output Payload:\n{json.dumps(waybar_output)}")
    print("\nWeather memory logs and CSV tracking pipelines written successfully.")

if __name__ == "__main__":
    main()
