"""
Productivity & Automation Tools for IGIRS AI.
Provides background voice timers, live weather via Open-Meteo / wttr.in,
and morning briefing synthesis.
"""
import time
import json
import logging
import threading
import urllib.request
import urllib.parse
from datetime import datetime
from typing import Dict, Any, Optional, Callable

logger = logging.getLogger("IGIRS.Productivity")

# Active timers tracking
_ACTIVE_TIMERS: Dict[str, threading.Timer] = {}

# WMO Weather Interpretation Codes
WMO_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Foggy",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Slight snowfall",
    73: "Moderate snowfall",
    75: "Heavy snowfall",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail"
}

def _play_timer_chime():
    """Plays an alert chime when a timer elapses."""
    try:
        import winsound
        # Upbeat dual-tone chime
        winsound.Beep(880, 150)
        winsound.Beep(1175, 200)
        winsound.Beep(1568, 300)
    except Exception:
        pass

def set_timer(
    seconds: int,
    label: str = "Timer",
    user_name: str = "Joshua",
    tts_callback: Optional[Callable[[str], None]] = None
) -> Dict[str, Any]:
    """
    Sets a background countdown timer that plays a chime and speaks when elapsed.
    """
    try:
        seconds = int(seconds)
        if seconds <= 0:
            return {"success": False, "message": "Timer duration must be greater than zero seconds."}

        # Format label and duration
        clean_label = label.strip() if label else "Timer"
        mins, secs = divmod(seconds, 60)
        hrs, mins = divmod(mins, 60)
        time_parts = []
        if hrs > 0:
            time_parts.append(f"{hrs} hour{'s' if hrs > 1 else ''}")
        if mins > 0:
            time_parts.append(f"{mins} minute{'s' if mins > 1 else ''}")
        if secs > 0 or not time_parts:
            time_parts.append(f"{secs} second{'s' if secs > 1 else ''}")
        duration_str = " and ".join(time_parts)

        timer_id = f"{clean_label}_{int(time.time())}"

        def _on_timer_complete():
            _ACTIVE_TIMERS.pop(timer_id, None)
            _play_timer_chime()
            alert_msg = f"Your {clean_label} for {duration_str} is up, {user_name}!"
            logger.info(f"Timer completed: {alert_msg}")
            if tts_callback:
                try:
                    tts_callback(alert_msg)
                except Exception as e:
                    logger.error(f"TTS callback failed for timer: {e}")

        t = threading.Timer(seconds, _on_timer_complete)
        t.daemon = True
        _ACTIVE_TIMERS[timer_id] = t
        t.start()

        return {
            "success": True,
            "timer_id": timer_id,
            "duration_seconds": seconds,
            "duration_formatted": duration_str,
            "label": clean_label,
            "message": f"Timer set for {duration_str} for '{clean_label}'."
        }
    except Exception as e:
        logger.error(f"Failed to set timer: {e}")
        return {"success": False, "error": str(e), "message": f"Failed to set timer: {e}"}

def cancel_all_timers() -> Dict[str, Any]:
    """Cancels all active background timers."""
    count = len(_ACTIVE_TIMERS)
    for timer in list(_ACTIVE_TIMERS.values()):
        try:
            timer.cancel()
        except Exception:
            pass
    _ACTIVE_TIMERS.clear()
    return {"success": True, "message": f"Cancelled {count} active timer(s)."}

def get_live_weather(city: Optional[str] = None) -> Dict[str, Any]:
    """
    Fetches real-time weather using Open-Meteo (with geocoding) or wttr.in fallback.
    Does not require any API key.
    """
    # 1. If explicit city is provided, try Open-Meteo Geocoding + Forecast
    if city and city.strip():
        city_query = city.strip()
        try:
            geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote_plus(city_query)}&count=1&language=en&format=json"
            req_geo = urllib.request.Request(geo_url, headers={"User-Agent": "IGIRS-AI/1.0"})
            with urllib.request.urlopen(req_geo, timeout=5) as resp:
                geo_data = json.loads(resp.read().decode("utf-8"))

            if "results" in geo_data and len(geo_data["results"]) > 0:
                loc = geo_data["results"][0]
                lat = loc["latitude"]
                lon = loc["longitude"]
                loc_name = loc.get("name", city_query)
                country = loc.get("country", "")
                admin = loc.get("admin1", "")
                display_location = f"{loc_name}, {admin} ({country})" if admin else f"{loc_name}, {country}"

                # Fetch current weather
                forecast_url = (
                    f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
                    f"&current=temperature_2m,relative_humidity_2m,apparent_temperature,is_day,weather_code,wind_speed_10m"
                    f"&timezone=auto"
                )
                req_w = urllib.request.Request(forecast_url, headers={"User-Agent": "IGIRS-AI/1.0"})
                with urllib.request.urlopen(req_w, timeout=5) as resp_w:
                    w_data = json.loads(resp_w.read().decode("utf-8"))

                current = w_data.get("current", {})
                temp_c = round(current.get("temperature_2m", 0), 1)
                temp_f = round((temp_c * 9/5) + 32, 1)
                feels_c = round(current.get("apparent_temperature", temp_c), 1)
                humidity = current.get("relative_humidity_2m", "N/A")
                wind_speed = current.get("wind_speed_10m", "N/A")
                weather_code = current.get("weather_code", 0)
                condition = WMO_CODES.get(weather_code, "Fair")

                spoken = f"In {loc_name}, it's {condition.lower()} and {temp_c}°C (feels like {feels_c}°C) with {humidity}% humidity."

                return {
                    "success": True,
                    "location": display_location,
                    "city": loc_name,
                    "temperature_c": temp_c,
                    "temperature_f": temp_f,
                    "feels_like_c": feels_c,
                    "condition": condition,
                    "humidity": f"{humidity}%",
                    "wind_speed": f"{wind_speed} km/h",
                    "message": spoken
                }
        except Exception as e:
            logger.warning(f"Open-Meteo lookup failed for {city_query}: {e}. Falling back to wttr.in.")

    # 2. Fallback or Local Auto-detection via wttr.in
    try:
        query_path = urllib.parse.quote_plus(city.strip()) if city and city.strip() else ""
        url = f"https://wttr.in/{query_path}?format=j1"
        req = urllib.request.Request(url, headers={"User-Agent": "curl/7.68.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        current = data.get("current_condition", [{}])[0]
        nearest = data.get("nearest_area", [{}])[0]
        loc_name = nearest.get("areaName", [{}])[0].get("value", city or "Local Area")
        country = nearest.get("country", [{}])[0].get("value", "")
        temp_c = current.get("temp_C", "N/A")
        temp_f = current.get("temp_F", "N/A")
        feels_c = current.get("FeelsLikeC", temp_c)
        humidity = current.get("humidity", "N/A")
        desc = current.get("weatherDesc", [{}])[0].get("value", "Clear")

        spoken = f"It's {desc.lower()} and {temp_c}°C in {loc_name}, with {humidity}% humidity."

        return {
            "success": True,
            "location": f"{loc_name}, {country}" if country else loc_name,
            "city": loc_name,
            "temperature_c": temp_c,
            "temperature_f": temp_f,
            "feels_like_c": feels_c,
            "condition": desc,
            "humidity": f"{humidity}%",
            "message": spoken
        }
    except Exception as e:
        logger.error(f"wttr.in fallback failed: {e}")

    # 3. Simple text fallback
    try:
        query_path = urllib.parse.quote_plus(city.strip()) if city and city.strip() else ""
        url = f"https://wttr.in/{query_path}?format=%C+%t+(Humidity:+%h)"
        req = urllib.request.Request(url, headers={"User-Agent": "curl/7.68.0"})
        with urllib.request.urlopen(req, timeout=4) as resp:
            text = resp.read().decode("utf-8").strip()
            return {
                "success": True,
                "location": city or "Local Area",
                "message": f"Current weather: {text}"
            }
    except Exception as e:
        logger.error(f"All weather endpoints failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "I'm unable to connect to the weather service right now. Please check your internet connection."
        }

def get_daily_briefing(
    user_name: str = "Joshua",
    telemetry: Optional[Dict[str, Any]] = None,
    notes: Optional[list] = None
) -> Dict[str, Any]:
    """
    Synthesizes a cohesive, natural morning or daily status briefing.
    """
    now = datetime.now()
    hour = now.hour
    if hour < 12:
        greeting = f"Good morning, {user_name}!"
    elif hour < 17:
        greeting = f"Good afternoon, {user_name}!"
    else:
        greeting = f"Good evening, {user_name}!"

    # Date and Time
    date_str = now.strftime("%A, %B %d")
    time_str = now.strftime("%I:%M %p")

    # Fetch live weather
    weather = get_live_weather()
    weather_summary = weather.get("message", "Weather data is currently unavailable.")

    # System Health
    telemetry = telemetry or {}
    battery_info = telemetry.get("battery_percent", "N/A")
    plugged_info = telemetry.get("battery_power_plugged", "")
    cpu_info = telemetry.get("cpu_usage_percent", "N/A")
    ram_info = telemetry.get("ram_usage_percent", "N/A")

    # Notes
    active_notes = notes or []
    notes_count = len(active_notes)

    # Construct clean human-spoken overview
    speech_parts = [
        f"{greeting} It's {time_str} on {date_str}.",
        f"Weather wise: {weather_summary}.",
        f"Your laptop battery is at {battery_info} ({plugged_info})." if battery_info != "N/A" else "",
        f"You have {notes_count} note{'s' if notes_count != 1 else ''} saved." if notes_count > 0 else "You're all clear with no pending notes."
    ]
    speech = " ".join([p for p in speech_parts if p])

    return {
        "greeting": greeting,
        "date": date_str,
        "time": time_str,
        "weather": weather,
        "battery": f"{battery_info} ({plugged_info})",
        "cpu_usage": cpu_info,
        "ram_usage": ram_info,
        "notes_count": notes_count,
        "briefing_speech": speech
    }
