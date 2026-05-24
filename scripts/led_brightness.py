"""Shared live brightness support for rgbmatrix scripts."""

from __future__ import annotations

import os
import time
from pathlib import Path

DEFAULT_BRIGHTNESS = 60
POLL_SECONDS = 0.15

_last_check = 0.0
_last_applied = None


def _coerce(value, default=DEFAULT_BRIGHTNESS, minimum=0):
    try:
        n = int(str(value).strip())
    except (TypeError, ValueError):
        n = default
    return max(minimum, min(100, n))


def _brightness_file():
    configured = os.environ.get("LED_BRIGHTNESS_FILE")
    if configured:
        return Path(configured)
    try:
        return Path(__file__).resolve().parent.parent / "web" / "brightness.txt"
    except NameError:
        return Path("web") / "brightness.txt"


def _read_file():
    try:
        return _brightness_file().read_text().strip()
    except OSError:
        return None


def read_initial_brightness(default=DEFAULT_BRIGHTNESS):
    """Return a hardware-safe initial brightness value in the range 1-100."""
    raw = os.environ.get("LED_BRIGHTNESS")
    if raw is None:
        raw = _read_file()
    return _coerce(raw, default=default, minimum=1)


def read_live_brightness(default=DEFAULT_BRIGHTNESS):
    """Return the current requested brightness, preserving 0 as an off signal."""
    raw = _read_file()
    if raw is None:
        raw = os.environ.get("LED_BRIGHTNESS")
    return _coerce(raw, default=default, minimum=0)


def apply_live_brightness(matrix, interval=POLL_SECONDS):
    """Apply changed brightness to a running matrix at most every interval."""
    global _last_check, _last_applied
    now = time.monotonic()
    if now - _last_check < interval:
        return _last_applied

    _last_check = now
    requested = read_live_brightness()
    hardware_value = max(1, requested)
    if hardware_value != _last_applied:
        try:
            matrix.brightness = hardware_value
            _last_applied = hardware_value
        except Exception:
            # Browser preview shims and older bindings may not support runtime
            # brightness. The canvas preview still handles brightness itself.
            pass
    return _last_applied
