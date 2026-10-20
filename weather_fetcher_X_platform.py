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

# ==================== CROSS-PLATFORM CONFIGURATION ====================
LATITUDE = 20.385
LONGITUDE = 72.911
API_URL = "https://api.open-meteo.com/v1/forecast"

# Detect Operating System and set CACHE_DIR dynamically
SYSTEM_OS = platform.system().lower()

if "win" in SYSTEM_OS:
    # Windows: Uses system TEMP directory. 
    # TIP: If building a Rainmeter skin, you can change this path directly to:
    # Path(os.path.expandvars(r"%USERPROFILE%\Documents\Rainmeter\Skins\YourSkinName\@Resources"))
    CACHE_DIR = Path(os.environ.get("LOCALAPPDATA", r"C:\Users\User\AppData\Local")) / "Temp" / "WeatherCache"
elif "bsd" in SYSTEM_OS or "linux" in SYSTEM_OS or "darwin" in SYSTEM_OS:
    # Linux, FreeBSD, OpenBSD, NetBSD, macOS
    CACHE_DIR = Path("/tmp")
else:
    # Generic fallback
    CACHE_DIR = Path("/tmp")

# Ensure the cache directory exists on Windows/BSD if it doesn't already
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
    "storm": "",         # Thunderstorm ## ⛈️is not showing right in dzen
}

def weather_icon(code, is_day):
    if code == 0:
        return ICONS["sun"] if is_day else ICONS["moon"]
    if code in (1, 2):
        return ICONS["partly_day"] if is_day else ICONS["partly_night"]
    if code == 3:
        return ICONS["cloud"]
    if code in (45, 48):
        return ICONS["fog"]
    if code in (51, 53, 55, 56, 57):
        return ICONS["drizzle"]
    if code in (61, 63, 65, 66, 67, 80, 81, 82):
        return ICONS["rain"]
    if code in (71, 73, 75, 77, 85, 86):
        return ICONS["snow"]
    if code in (95, 96, 99):
        return ICONS["storm"]
    return ICONS["cloud"]

def moon_phase():
    now = datetime.now(timezone.utc)
    new_moon = datetime(2000, 1, 6, 18, 14, tzinfo=timezone.utc)
    synodic_month = 29.530588853

    age = ((now - new_moon).total_seconds() / 86400) % synodic_month
    fraction = age / synodic_month
    illumination = (1 - math.cos(2 * math.pi * fraction)) / 2 * 100

    if fraction < 0.0625 or fraction >= 0.9375:
        m_glyph, name = "", "New Moon"
    elif fraction < 0.1875:
        m_glyph, name = "", "Waxing Crescent"
    elif fraction < 0.3125:
        m_glyph, name = "", "First Quarter"
    elif fraction < 0.4375:
        m_glyph, name = "", "Waxing Gibbous"
    elif fraction < 0.5625:
        m_glyph, name = "", "Full Moon"
    elif fraction < 0.6875:
        m_glyph, name = "", "Waning Gibbous"
    elif fraction < 0.8125:
        m_glyph, name = "", "Last Quarter"
    else:
        m_glyph, name = "", "Waning Crescent"

    return f"{m_glyph} {name} ({illumination:.0f}%)"

def atomic_write(filename, content):
    destination = CACHE_DIR / filename
    fd, temp_name = tempfile.mkstemp(dir=str(CACHE_DIR))

    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            file.write(content + "\n")
        os.replace(temp_name, destination)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)

def main():
    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "current": "temperature_2m,wind_speed_10m,wind_direction_10m,is_day,weather_code",
        "hourly": "temperature_2m,weather_code",
        "daily": "temperature_2m_max,temperature_2m_min,weather_code",
        "timezone": "auto",
        "forecast_days": 5,
        "temperature_unit": "celsius",
        "wind_speed_unit": "ms"
    }    
    
    try:
        response = requests.get(API_URL, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()
    except Exception:
        data = None

    m_phase = moon_phase()

    # Fallback if network fails entirely
    if data is None:
        atomic_write("weather_icon_cache", "")
        atomic_write("weather_temp_cache", "--°C")
        atomic_write("weather_moon_phase", m_phase)
        atomic_write("windspeed", "0.00 m/s")
        atomic_write("weather_time_status", "day")
        
        waybar_output = {"text": " --°C", "tooltip": f"Offline Fallback Mode\n🌙 Lunar: {m_phase}"}
        print(json.dumps(waybar_output))
        return

    # Dump the JSON cache file cleanly on success to the platform's cache directory
    atomic_write("weather_api_cache.json", json.dumps(data, indent=2))

    current = data.get("current", {})
    required = ("temperature_2m", "wind_speed_10m", "wind_direction_10m", "is_day", "weather_code")
    if any(current.get(key) is None for key in required):
        raise ValueError("Required weather fields are missing from API response")

    temperature = current.get("temperature_2m", 0.0)
    wind = current.get("wind_speed_10m", 0.0)
    wind_dir= current.get("wind_direction_10m", 0.0)
    weather_code = current.get("weather_code", 0)
    is_day = current.get("is_day", 1)
    
    icon = weather_icon(weather_code, bool(is_day))

    # Maintain atomic writes for dashboard text files across platforms
    atomic_write("weather_icon_cache", icon)
    atomic_write("weather_temp_cache", f"{round(temperature)}°C")
    atomic_write("weather_moon_phase", m_phase)
    atomic_write("windspeed", f"{wind:.2f} m/s")
    atomic_write("weather_time_status", "day" if is_day == 1 else "night")

# Extract 2-Day forecast metrics for Rainmeter safely with text descriptions
    try:
        daily_data = data.get("daily", {})
        d1_date = daily_data.get("time", ["--"])[0]
        d2_date = daily_data.get("time", ["--"])[1]
        d1_max = daily_data.get("temperature_2m_max", ["--"])[0]
        d2_max = daily_data.get("temperature_2m_max", ["--"])[1]
        d1_min = daily_data.get("temperature_2m_min", ["--"])[0]
        d2_min = daily_data.get("temperature_2m_min", ["--"])[1]
        d1_code = daily_data.get("weather_code", [0])[0]
        d2_code = daily_data.get("weather_code", [0])[1]
        
        # WMO Weather Code Dictionary mapping
        wmo_desc = {
            0: "Clear Sky", 1: "Mainly Clear", 2: "Partly Cloudy", 3: "Overcast",
            45: "Foggy", 48: "Rime Fog", 51: "Light Drizzle", 53: "Moderate Drizzle",
            55: "Dense Drizzle", 61: "Slight Rain", 63: "Moderate Rain", 65: "Heavy Rain",
            71: "Slight Snow", 73: "Mod Snow", 75: "Heavy Snow", 77: "Snow Grains",
            80: "Slight Showers", 81: "Mod Showers", 82: "Violent Showers",
            85: "Slight Snow Showers", 86: "Heavy Snow Showers",
            95: "Thunderstorm", 96: "Storm + Hail", 99: "Severe Storm"
        }
        
        d1_txt = wmo_desc.get(int(d1_code), "Unknown")
        d2_txt = wmo_desc.get(int(d2_code), "Unknown")
        
        # Build the descriptive text layout Rainmeter needs for the tooltip
        forecast_text = (
            f"📅 {d1_date} (Today)\n"
            f"✨ Condition: {d1_txt}\n"
            f"🔺 Max: {round(d1_max)}°C\n"
            f"🔻 Min: {round(d1_min)}°C\n\n"
            f"📅 {d2_date} (Tomorrow)\n"
            f"✨ Condition: {d2_txt}\n"
            f"🔺 Max: {round(d2_max)}°C\n"
            f"🔻 Min: {round(d2_min)}°C"
        )
        atomic_write("weather_forecast_cache", forecast_text)
    except Exception:
        atomic_write("weather_forecast_cache", "Forecast Details Unavailable")

    # Native Waybar / Dashboard Output Structure
    waybar_output = {
        "text": f"{icon} {round(temperature)}°C",
        "tooltip": f"✨ Condition: Clear Sky\n💨 Wind Speed: {wind:.1f} m/s\n🌙 Moon Phase: {m_phase}",
        "class": "weather",
        "percentage": round(temperature)
    }
    print(json.dumps(waybar_output, ensure_ascii=False))

if __name__ == '__main__': main()
