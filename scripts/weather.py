#!/usr/bin/env python3
"""Waterloo, Ontario live weather display.

Pulls current conditions from Open-Meteo (no API key required) for
lat=43.4643, lon=-80.5204, picks the matching shared scene renderer, and shows
the live temperature in the top-right corner.
"""

from __future__ import annotations

import datetime as dt
import json
import time
import urllib.error
import urllib.request

from weather_scene import (
    CLOUD_NONE,
    CLOUD_OVERCAST,
    CLOUD_PARTIAL,
    COND_CLEAR,
    COND_CLOUDY,
    COND_RAIN,
    COND_SNOW,
    COND_STORM,
    FRAME_DELAY,
    PHASE_DAY,
    PHASE_NIGHT,
    PHASE_SUNRISE,
    PHASE_SUNSET,
    RAIN_DRIZZLE,
    RAIN_SHOWER,
    RAIN_STEADY,
    active_night_windows,
    create_matrix,
    draw_condition_scene,
    parse_open_meteo_time,
)

# ─── live weather fetch (Open-Meteo) ───────────────────────────────────────

LAT, LON = 43.4643, -80.5204  # Waterloo, Ontario
WEATHER_URL = (
    "https://api.open-meteo.com/v1/forecast"
    "?latitude={lat}&longitude={lon}"
    "&current=temperature_2m,weather_code,is_day"
    "&daily=sunrise,sunset"
    "&forecast_days=1"
    "&timezone=auto"
).format(lat=LAT, lon=LON)

REFRESH_SECONDS = 600  # pull new conditions every 10 minutes
HTTP_TIMEOUT = 10
TWILIGHT_WINDOW = dt.timedelta(minutes=45)


def classify_phase(current_time, sunrise, sunset, is_day):
    now = parse_open_meteo_time(current_time)
    sunrise_time = parse_open_meteo_time(sunrise)
    sunset_time = parse_open_meteo_time(sunset)

    if now is None:
        now = dt.datetime.now()
    if any(
        value is not None and (value.tzinfo is None) != (now.tzinfo is None)
        for value in (sunrise_time, sunset_time)
    ):
        now = now.replace(tzinfo=None)
        if sunrise_time is not None:
            sunrise_time = sunrise_time.replace(tzinfo=None)
        if sunset_time is not None:
            sunset_time = sunset_time.replace(tzinfo=None)
    if sunrise_time is not None and abs(now - sunrise_time) <= TWILIGHT_WINDOW:
        return PHASE_SUNRISE
    if sunset_time is not None and abs(now - sunset_time) <= TWILIGHT_WINDOW:
        return PHASE_SUNSET
    return PHASE_DAY if is_day else PHASE_NIGHT


# WMO weather codes -> (short label, condition, cloud cover, rain style).
def classify_condition(weather_code):
    c = weather_code
    if c == 0:
        return ("CLR", COND_CLEAR, CLOUD_NONE, RAIN_STEADY)
    if c in (1, 2):
        return ("PCLD", COND_CLEAR, CLOUD_PARTIAL, RAIN_STEADY)
    if c == 3:
        return ("OVC", COND_CLOUDY, CLOUD_OVERCAST, RAIN_STEADY)
    if c in (45, 48):
        return ("FOG", COND_CLOUDY, CLOUD_OVERCAST, RAIN_STEADY)
    if c in (51, 53, 55, 56, 57):
        return ("DZL", COND_RAIN, CLOUD_OVERCAST, RAIN_DRIZZLE)
    if c in (61, 63, 65, 66, 67):
        return ("RAIN", COND_RAIN, CLOUD_OVERCAST, RAIN_STEADY)
    if c in (80, 81, 82):
        return ("SHWR", COND_RAIN, CLOUD_OVERCAST, RAIN_SHOWER)
    if c in (71, 73, 75, 77, 85, 86):
        return ("SNOW", COND_SNOW, CLOUD_OVERCAST, RAIN_STEADY)
    if c in (95, 96, 99):
        return ("STRM", COND_STORM, CLOUD_OVERCAST, RAIN_SHOWER)
    return ("?", COND_CLOUDY, CLOUD_OVERCAST, RAIN_STEADY)


def fetch_weather():
    """Return a current weather dict or None on failure."""
    try:
        with urllib.request.urlopen(WEATHER_URL, timeout=HTTP_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        cur = data["current"]
        daily = data.get("daily", {})
        return {
            "temp_c": int(round(cur["temperature_2m"])),
            "weather_code": int(cur["weather_code"]),
            "is_day": bool(cur["is_day"]),
            "current_time": cur.get("time"),
            "sunrise": daily.get("sunrise", [None])[0],
            "sunset": daily.get("sunset", [None])[0],
        }
    except (urllib.error.URLError, ValueError, KeyError, TypeError, OSError):
        return None


def make_label(temp_c, _cond):
    return "{:d}\xb0C".format(temp_c)


def make_render_state(reading):
    cond_label, condition, clouds, rain_style = classify_condition(
        reading["weather_code"]
    )
    phase = classify_phase(
        reading.get("current_time"),
        reading.get("sunrise"),
        reading.get("sunset"),
        reading.get("is_day"),
    )
    night_lighting = ()
    if phase == PHASE_NIGHT:
        night_lighting = active_night_windows(
            reading.get("current_time"),
            reading.get("sunset"),
            reading.get("sunrise"),
        )
    return (
        make_label(reading["temp_c"], cond_label),
        condition,
        phase,
        clouds,
        rain_style,
        night_lighting,
    )


# ─── main loop ─────────────────────────────────────────────────────────────


def main():
    # weather_scene loads FONT at import time. RGBMatrix drops privileges to
    # user "daemon", so fonts and /home/pi files must be loaded before here.
    matrix = create_matrix(gpio_slowdown=2, pwm_bits=8)
    canvas = matrix.CreateFrameCanvas()

    current = fetch_weather()
    if current is None:
        # No network yet — fall back to a neutral overcast scene until next try.
        label = "--"
        condition = COND_CLOUDY
        phase = PHASE_DAY
        clouds = CLOUD_OVERCAST
        rain_style = RAIN_STEADY
        night_lighting = ()
    else:
        label, condition, phase, clouds, rain_style, night_lighting = make_render_state(
            current
        )

    animation_start = time.monotonic()
    next_frame_time = animation_start
    last_fetch = animation_start

    try:
        while True:
            now = time.monotonic()
            frame = int((now - animation_start) / FRAME_DELAY)

            canvas.Clear()
            draw_condition_scene(
                canvas,
                frame,
                condition,
                phase,
                clouds,
                label,
                rain_style,
                night_lighting,
            )
            canvas = matrix.SwapOnVSync(canvas)

            now = time.monotonic()
            if now - last_fetch >= REFRESH_SECONDS:
                result = fetch_weather()
                last_fetch = time.monotonic()
                if result is not None:
                    label, condition, phase, clouds, rain_style, night_lighting = (
                        make_render_state(result)
                    )
                # On failure, keep showing the last good reading.

            next_frame_time += FRAME_DELAY
            sleep_for = next_frame_time - time.monotonic()
            if sleep_for > 0:
                time.sleep(sleep_for)
            else:
                next_frame_time = time.monotonic()
    except KeyboardInterrupt:
        matrix.Clear()


if __name__ == "__main__":
    main()
