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
LAT = XX.LAT	# EDIT WITH YOUR COORDINATES [LATITUDE]
LON = XX.LON   # EDIT WITH YOUR COORDINATES [LONGITUDE]
API_URL = "https://api.open-meteo.com/v1/forecast"

# Detect Operating System and set CACHE_DIR dynamically
SYSTEM_OS = platform.system().lower()

if "win" in SYSTEM_OS:
    CACHE_DIR = Path(os.environ.get("LOCALAPPDATA", r"C:\Users\User\AppData\Local")) / "Temp" / "WeatherCache"
elif "bsd" in SYSTEM_OS or "linux" in SYSTEM_OS or "darwin" in SYSTEM_OS:
    CACHE_DIR = Path("/tmp")
else:
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
    """Converts meteorological degrees to 16-point text direction and standard layout arrows."""
    degrees = (degrees % 360 + 360) % 360
    points = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    arrows = ["↓", "↙", "↙", "↙", "←", "↖", "↖", "↖", "↑", "↗", "↗", "↗", "→", "↘", "↘", "↘"]
    index = int((degrees + 11.25) / 22.5) % 16
    return points[index], arrows[index]

def get_visible_width(text):
    """Accurately maps the display matrix width of icons and characters."""
    width = 0
    for char in text:
        if ord(char) in [0xf185, 0xf186, 0xe21d, 0xec7e, 0xe312, 0xe30d, 0xe239, 0xf2dc, 0xe322, 0xef03, 0xef04] or char in ["↓", "↙", "←", "↖", "↑", "↗", "→", "↘"]:
            width += 1
        else:
            width += 1 if ord(char) < 0x2e80 else 2
    return width

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
        if os.path.exists(temp_name): os.unlink(temp_name)
def main():
    params = {
        "latitude": LAT,
        "longitude": LON,
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
        atomic_write("weather_condition_cache", "Unknown")
        atomic_write("weather_moon_phase_cache", m_phase)
        atomic_write("windspeed", "0.00 m/s")
        atomic_write("weather_time_status", "day")
        
        waybar_output = {
            "text": " --°C", 
            "tooltip": f"Offline Fallback Mode\n🌙 Lunar: {m_phase}", 
            "class": "weather", 
            "percentage": 0
        }
        import sys
        if len(sys.argv) > 1 and sys.argv[1] == "--json-only":
            print(json.dumps(waybar_output))
        else:
            fallback_report = [
                "Temp:            --°C",
                "Condition:      Offline Fallback Mode",
                "Wind:           0.00 m/s (N ↓)",
                f"Lunar Phase:    {m_phase}"
            ]
            fallback_len = max(get_visible_width(l) for l in fallback_report)
            print("*" * fallback_len)
            for l in fallback_report: print(l)
            print("*" * fallback_len)
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
    wind_dir = current.get("wind_direction_10m", 0.0)
    weather_code = current.get("weather_code", 0)
    is_day = current.get("is_day", 1)
    
    icon = weather_icon(weather_code, bool(is_day))

    # Safely resolve current weather condition description text
    condition_text = WMO_TEXT_MAP.get(int(weather_code), "Unknown")

    # Calculate 16-point wind properties
    wind_text, wind_arrow = get_16_point_compass(wind_dir)

    # Maintain atomic writes for dashboard text files across platforms
    atomic_write("weather_icon_cache", icon)
    atomic_write("weather_temp_cache", f"{round(temperature)}°C")
    atomic_write("weather_condition_cache", condition_text)
    atomic_write("weather_moon_phase_cache", m_phase)
    atomic_write("windspeed", f"{wind:.2f} m/s")
    atomic_write("wind_direction_cache", f"{wind_text} {wind_arrow}")
    atomic_write("weather_time_status", "day" if is_day == 1 else "night")

    # Extract 2-Day forecast metrics safely using positional indexing
    try:
        daily_data = data.get("daily", {})
        d1_date = daily_data.get("time", ["--"])[0]
        d2_date = daily_data.get("time", ["--"])[1]
        d1_max = daily_data.get("temperature_2m_max", [0.0])[0]
        d2_max = daily_data.get("temperature_2m_max", [0.0])[1]
        d1_min = daily_data.get("temperature_2m_min", [0.0])[0]
        d2_min = daily_data.get("temperature_2m_min", [0.0])[1]
        d1_code = daily_data.get("weather_code", [0])[0]
        d2_code = daily_data.get("weather_code", [0])[1]
        
        d1_txt = WMO_TEXT_MAP.get(int(d1_code), "Unknown")
        d2_txt = WMO_TEXT_MAP.get(int(d2_code), "Unknown")
        
        # Safe string styling separation using clean .format maps
        # Removed span formatting entirely from the date row to guarantee error-free rendering
        forecast_text = (
            "📅 {} (Today)\n"
            "✨ Condition: {}\n"
            "🔺 Max: <span color='#ff6c6b'>{}°C</span>\n"
            "🔻 Min: <span color='#98be65'>{}°C</span>\n\n"
            "📅 {} (Tomorrow)\n"
            "✨ Condition: {}\n"
            "🔺 Max: <span color='#ff6c6b'>{}°C</span>\n"
            "🔻 Min: <span color='#98be65'>{}°C</span>"
        ).format(
            str(d1_date), str(d1_txt), round(d1_max), round(d1_min),
            str(d2_date), str(d2_txt), round(d2_max), round(d2_min)
        )

        atomic_write("weather_forecast_cache", forecast_text)
    except Exception:
        forecast_text = "Forecast Details Unavailable"
        atomic_write("weather_forecast_cache", forecast_text)

    # Native Waybar JSON output payload structure
    waybar_output = {
        "text": f"{icon} {round(temperature)}°C",
        "tooltip": f"✨ Condition: {condition_text}\n💨 Wind Speed: {wind:.1f} m/s ({wind_text} {wind_arrow})\n🌙 Moon Phase: {m_phase}\n\n{forecast_text}",
        "class": "weather",
        "percentage": int(round(temperature))
    }

    # ------------------------------------------------------------------
    # SWITCH OUTPUT MODES DYNAMICALLY BASED ON ARGUMENTS
    # ------------------------------------------------------------------
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--json-only":
        # Waybar Mode: Print ONLY the pristine JSON string
        print(json.dumps(waybar_output))
    else:
        # Terminal Mode: Print the visually boxed asterisks report AND the json
        report_lines = [
            f"Temp:           {icon} {round(temperature)}°C",
            f"Condition:      {condition_text}",
            f"Wind:           {wind:.2f} m/s ({wind_text} {wind_arrow})",
            f"Lunar Phase:    {m_phase}"
        ]
        max_len = max(get_visible_width(line) for line in report_lines)
        dynamic_border = "*" * max_len

        print(dynamic_border)
        for line in report_lines: print(line)
        print(dynamic_border)
        print(json.dumps(waybar_output))

if __name__ == "__main__":
    main()
