"""Weather service abstraction.

WEATHER_MODE=OPENWEATHER uses the OpenWeather current-weather API.
WEATHER_MODE=DEMO_WEATHER (default) returns clearly-labelled deterministic
sample values — never presented as live data.
"""
import hashlib
from datetime import datetime, timezone

import httpx

from app.config import settings

# Approximate monsoon-season baselines for the demo districts (labelled DEMO).
DEMO_BASE = {
    "Nashik": {"temp": 27.0, "humidity": 72.0, "rain": 4.0},
    "Pune": {"temp": 28.0, "humidity": 66.0, "rain": 2.0},
    "Ahmednagar": {"temp": 29.0, "humidity": 60.0, "rain": 1.0},
    "Nagpur": {"temp": 31.0, "humidity": 64.0, "rain": 3.0},
    "Kolhapur": {"temp": 26.0, "humidity": 80.0, "rain": 8.0},
}


def _demo_weather(location: str | None) -> dict:
    base = DEMO_BASE.get(location or "", DEMO_BASE["Pune"])
    # Deterministic per-day wiggle so charts look alive but stay reproducible.
    day = datetime.now(timezone.utc).strftime("%Y%m%d")
    digest = hashlib.sha256(f"{location}:{day}".encode()).hexdigest()
    wiggle = (int(digest[:4], 16) % 200) / 100.0 - 1.0  # -1..1
    return {
        "temperature": round(base["temp"] + wiggle, 1),
        "humidity": round(min(96, max(35, base["humidity"] + wiggle * 8)), 1),
        "rainfall_24h": round(max(0.0, base["rain"] + wiggle * 2), 1),
        "mode": "DEMO_WEATHER",
        "retrieved_at": datetime.now(timezone.utc),
        "source": "Demo sample data — not live weather",
    }


def get_weather(latitude: float | None, longitude: float | None,
                location: str | None = None) -> dict:
    if settings.WEATHER_MODE == "OPENWEATHER" and settings.OPENWEATHER_API_KEY:
        return _openweather(latitude, longitude, location)
    return _demo_weather(location)


def _openweather(latitude: float | None, longitude: float | None,
                 location: str | None) -> dict:
    params = {"appid": settings.OPENWEATHER_API_KEY, "units": "metric"}
    if latitude is not None and longitude is not None:
        params.update({"lat": latitude, "lon": longitude})
    elif location:
        params["q"] = location
    else:
        return _demo_weather(location)
    try:
        resp = httpx.get(f"{settings.OPENWEATHER_BASE_URL}/weather", params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        main = data.get("main", {})
        return {
            "temperature": float(main.get("temp", 0.0)),
            "humidity": float(main.get("humidity", 0.0)),
            "rainfall_24h": float((data.get("rain") or {}).get("1h", 0.0)) * 24,
            "mode": "OPENWEATHER",
            "retrieved_at": datetime.now(timezone.utc),
            "source": "OpenWeather",
        }
    except Exception as exc:
        print(f"[Agricure] Weather API failed ({exc}) — falling back to DEMO_WEATHER.")
        fallback = _demo_weather(location)
        fallback["source"] = "OpenWeather failed — demo sample data"
        return fallback
