#!/usr/bin/env python3
"""Standalone CMH weather overlay tester for 64x32 RGB LED matrices.

This file intentionally imports the shared renderer used by scripts/weather.py
so the offline scene cycle stays in lockstep with the live Pi display.
"""

from __future__ import annotations

import time

import weather_scene as scene

ROWS = scene.ROWS
COLS = scene.COLS
CHAIN_LENGTH = scene.CHAIN_LENGTH
PARALLEL = scene.PARALLEL
W = scene.W
H = scene.H
FRAME_DELAY = scene.FRAME_DELAY
FRAMES_PER_SCENE = scene.FRAMES_PER_SCENE

DEMO_NIGHT_SUNSET = "2026-01-15T18:00"
DEMO_NIGHT_SUNRISE = "2026-01-16T07:30"
DEMO_NIGHT_LIGHTING_EARLY = scene.active_night_windows(
    "2026-01-15T19:00",
    DEMO_NIGHT_SUNSET,
    DEMO_NIGHT_SUNRISE,
)
DEMO_NIGHT_LIGHTING_DEEP = scene.active_night_windows(
    "2026-01-16T01:00",
    DEMO_NIGHT_SUNSET,
    DEMO_NIGHT_SUNRISE,
)
DEMO_NIGHT_LIGHTING_PREDAWN = scene.active_night_windows(
    "2026-01-16T06:30",
    DEMO_NIGHT_SUNSET,
    DEMO_NIGHT_SUNRISE,
)


def create_matrix():
    return scene.create_matrix(gpio_slowdown=4, pwm_bits=11)


def draw_sunny(c, frame):
    scene.draw_condition_scene(
        c, frame, scene.COND_CLEAR, scene.PHASE_DAY, scene.CLOUD_NONE, "18C CLR"
    )


def draw_partly_cloudy(c, frame):
    scene.draw_condition_scene(
        c, frame, scene.COND_CLEAR, scene.PHASE_DAY, scene.CLOUD_PARTIAL, "18C PCLD"
    )


def draw_clear_sunrise(c, frame):
    scene.draw_condition_scene(
        c, frame, scene.COND_CLEAR, scene.PHASE_SUNRISE, scene.CLOUD_NONE, "18C CLR"
    )


def draw_partly_cloudy_sunset(c, frame):
    scene.draw_condition_scene(
        c, frame, scene.COND_CLEAR, scene.PHASE_SUNSET, scene.CLOUD_PARTIAL, "14C PCLD"
    )


def draw_cloudy_sunset(c, frame):
    scene.draw_condition_scene(
        c, frame, scene.COND_CLEAR, scene.PHASE_SUNSET, scene.CLOUD_OVERCAST, "14C CLD"
    )


def draw_cloudy(c, frame):
    scene.draw_condition_scene(
        c, frame, scene.COND_CLEAR, scene.PHASE_DAY, scene.CLOUD_OVERCAST, "14C CLD"
    )


def draw_cloudy_night(c, frame):
    scene.draw_condition_scene(
        c,
        frame,
        scene.COND_CLEAR,
        scene.PHASE_NIGHT,
        scene.CLOUD_OVERCAST,
        "12C CLD",
        night_lighting=DEMO_NIGHT_LIGHTING_DEEP,
    )


def draw_drizzle(c, frame):
    scene.draw_condition_scene(
        c,
        frame,
        scene.COND_RAIN,
        scene.PHASE_DAY,
        scene.CLOUD_OVERCAST,
        "9C DZL",
        scene.RAIN_DRIZZLE,
    )


def draw_rainy(c, frame):
    scene.draw_condition_scene(
        c,
        frame,
        scene.COND_RAIN,
        scene.PHASE_DAY,
        scene.CLOUD_OVERCAST,
        "9C RAIN",
        scene.RAIN_STEADY,
    )


def draw_showers(c, frame):
    scene.draw_condition_scene(
        c,
        frame,
        scene.COND_RAIN,
        scene.PHASE_DAY,
        scene.CLOUD_OVERCAST,
        "9C SHWR",
        scene.RAIN_SHOWER,
    )


def draw_rain_night(c, frame):
    scene.draw_condition_scene(
        c,
        frame,
        scene.COND_RAIN,
        scene.PHASE_NIGHT,
        scene.CLOUD_OVERCAST,
        "9C RAIN",
        scene.RAIN_STEADY,
        DEMO_NIGHT_LIGHTING_DEEP,
    )


def draw_snowy(c, frame):
    scene.draw_condition_scene(
        c, frame, scene.COND_SNOW, scene.PHASE_DAY, scene.CLOUD_OVERCAST, "-3C SNW"
    )


def draw_storm_sunset(c, frame):
    scene.draw_condition_scene(
        c, frame, scene.COND_STORM, scene.PHASE_SUNSET, scene.CLOUD_OVERCAST, "11C STRM"
    )


def draw_storm_night(c, frame):
    scene.draw_condition_scene(
        c,
        frame,
        scene.COND_STORM,
        scene.PHASE_NIGHT,
        scene.CLOUD_OVERCAST,
        "11C STRM",
        night_lighting=DEMO_NIGHT_LIGHTING_DEEP,
    )


def draw_night(c, frame):
    scene.draw_condition_scene(
        c,
        frame,
        scene.COND_CLEAR,
        scene.PHASE_NIGHT,
        scene.CLOUD_NONE,
        "12C CLR",
        night_lighting=DEMO_NIGHT_LIGHTING_DEEP,
    )


def draw_night_early(c, frame):
    scene.draw_condition_scene(
        c,
        frame,
        scene.COND_CLEAR,
        scene.PHASE_NIGHT,
        scene.CLOUD_NONE,
        "12C CLR",
        night_lighting=DEMO_NIGHT_LIGHTING_EARLY,
    )


def draw_night_predawn(c, frame):
    scene.draw_condition_scene(
        c,
        frame,
        scene.COND_CLEAR,
        scene.PHASE_NIGHT,
        scene.CLOUD_NONE,
        "12C CLR",
        night_lighting=DEMO_NIGHT_LIGHTING_PREDAWN,
    )


SCENES = (
    draw_sunny,
    draw_partly_cloudy,
    draw_cloudy,
    draw_clear_sunrise,
    draw_partly_cloudy_sunset,
    draw_cloudy_sunset,
    draw_cloudy_night,
    draw_drizzle,
    draw_rainy,
    draw_showers,
    draw_rain_night,
    draw_snowy,
    draw_storm_sunset,
    draw_storm_night,
    draw_night,
    draw_night_early,
    draw_night_predawn,
)


def main():
    matrix = create_matrix()
    canvas = matrix.CreateFrameCanvas()
    scene_idx = 0
    scene_frame = 0

    print("Cycling shared CMH weather scenes. Press Stop or Ctrl+C to stop.")
    try:
        while True:
            canvas.Clear()
            SCENES[scene_idx](canvas, scene_frame)
            canvas = matrix.SwapOnVSync(canvas)

            scene_frame += 1
            if scene_frame >= FRAMES_PER_SCENE:
                scene_frame = 0
                scene_idx = (scene_idx + 1) % len(SCENES)
            time.sleep(FRAME_DELAY)
    except KeyboardInterrupt:
        matrix.Clear()


if __name__ == "__main__":
    main()
