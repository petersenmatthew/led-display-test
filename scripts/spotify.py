#!/usr/bin/env python3
"""Spotify now-playing display for a 64x32 RGB LED matrix.

A rotating CD on the left whose face is the album art of whatever is
playing LIVE on your Spotify account, with the track title, artist,
and a progress bar on the right. The disk spins while music plays and
stops when paused.

One-time setup (creates spotify_config.json at the repo root):

    python3 scripts/spotify_auth.py

Needs Pillow on the Pi for album-art decoding: sudo apt install python3-pil
Without config/network it falls back to a demo rainbow disk, so the
browser preview still shows the full animation.
"""

from __future__ import annotations

import base64
import colorsys
import json
import math
import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics
from led_brightness import apply_live_brightness, read_initial_brightness

ROWS = 32
COLS = 64

POLL_SECONDS = 3.0        # how often to ask Spotify what's playing
SPIN_SECONDS = 3.6        # one full disk revolution while playing
FRAME_DELAY = 1.0 / 30.0

# Disk geometry (left side of the panel).
DISK_CX = 15.5
DISK_CY = 15.5
DISK_R = 13.5
HOLE_R = 2.0              # spindle hole (background shows through)
HUB_R = 4.0               # silver hub ring around the hole
DISK_FRAMES = 48          # precomputed rotation steps
ART_SIZE = 32             # album art is sampled from this square

# Text zone (right side).
TXT_X0 = 31
TXT_W = COLS - TXT_X0

SCROLL_PX_PER_S = 12.0
SCROLL_GAP = 16

SPOTIFY_GREEN = (30, 215, 96)

TOKEN_URL = "https://accounts.spotify.com/api/token"
NOW_PLAYING_URL = (
    "https://api.spotify.com/v1/me/player/currently-playing"
    "?additional_types=track,episode"
)
HTTP_TIMEOUT = 10


# ─── config / fonts (must load before RGBMatrix drops privileges) ───────────

def repo_root():
    try:
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    except NameError:  # browser preview has no __file__
        return os.getcwd()


def load_config():
    """Return {client_id, client_secret, refresh_token} or None."""
    candidates = []
    configured = os.environ.get("SPOTIFY_CONFIG")
    if configured:
        candidates.append(configured)
    candidates.append(os.path.join(repo_root(), "spotify_config.json"))
    for path in candidates:
        try:
            with open(path) as fh:
                cfg = json.load(fh)
            if all(k in cfg for k in ("client_id", "client_secret", "refresh_token")):
                return cfg
        except (OSError, ValueError):
            continue
    return None


def load_font(name):
    font = graphics.Font()
    candidates = [
        os.path.join(repo_root(), "fonts", name),
        os.path.join("fonts", name),
        name,
    ]
    for path in candidates:
        try:
            font.LoadFont(path)
            return font
        except Exception:
            continue
    raise RuntimeError("could not load font %s" % name)


CONFIG = load_config()
FONT_TITLE = load_font("5x7.bdf")
FONT_SMALL = load_font("4x6.bdf")


# ─── Spotify client ──────────────────────────────────────────────────────────

class SpotifyClient:
    def __init__(self, cfg):
        self.client_id = cfg["client_id"]
        self.client_secret = cfg["client_secret"]
        self.refresh_token = cfg["refresh_token"]
        self.access_token = None
        self.token_expiry = 0.0

    def _basic_auth(self):
        raw = "%s:%s" % (self.client_id, self.client_secret)
        return "Basic " + base64.b64encode(raw.encode()).decode()

    def _refresh_access_token(self):
        body = urllib.parse.urlencode({
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
        }).encode()
        req = urllib.request.Request(TOKEN_URL, data=body, headers={
            "Authorization": self._basic_auth(),
            "Content-Type": "application/x-www-form-urlencoded",
        })
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        self.access_token = data["access_token"]
        self.token_expiry = time.monotonic() + int(data.get("expires_in", 3600)) - 60
        if data.get("refresh_token"):
            self.refresh_token = data["refresh_token"]

    def _get(self, url):
        if not self.access_token or time.monotonic() >= self.token_expiry:
            self._refresh_access_token()
        req = urllib.request.Request(url, headers={
            "Authorization": "Bearer " + self.access_token,
        })
        try:
            with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
                if resp.status == 204:
                    return None
                raw = resp.read()
                return json.loads(raw.decode("utf-8")) if raw else None
        except urllib.error.HTTPError as exc:
            if exc.code == 401:  # stale token — refresh once and retry
                self._refresh_access_token()
                req = urllib.request.Request(url, headers={
                    "Authorization": "Bearer " + self.access_token,
                })
                with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
                    if resp.status == 204:
                        return None
                    raw = resp.read()
                    return json.loads(raw.decode("utf-8")) if raw else None
            raise

    def currently_playing(self):
        """Return a simplified dict, or None when nothing is playing."""
        data = self._get(NOW_PLAYING_URL)
        item = (data or {}).get("item")
        if not data or not item:
            return None
        if item.get("type") == "episode":  # podcasts
            artist = item.get("show", {}).get("name", "")
            images = item.get("images", [])
        else:
            artist = ", ".join(a["name"] for a in item.get("artists", []))
            images = item.get("album", {}).get("images", [])
        # images are ordered largest-first; the smallest (64px) is plenty.
        art_url = images[-1]["url"] if images else None
        return {
            "id": item.get("id") or item.get("uri", ""),
            "title": item.get("name", "?"),
            "artist": artist,
            "art_url": art_url,
            "playing": bool(data.get("is_playing")),
            "progress_ms": int(data.get("progress_ms") or 0),
            "duration_ms": int(item.get("duration_ms") or 0),
        }


def prep_art(img):
    """Prep a PIL cover for the LED disc; returns ART_SIZE rows of (r, g, b).

    Dark covers disappear on an LED panel at this size — stretch the levels
    and boost saturation so the disc face stays readable.
    """
    from PIL import ImageEnhance, ImageOps
    img = img.convert("RGB")
    img = ImageOps.autocontrast(img, cutoff=1)
    img = ImageEnhance.Color(img).enhance(1.35)
    img = ImageEnhance.Brightness(img).enhance(1.15)
    img = img.resize((ART_SIZE, ART_SIZE))
    px = list(img.getdata())
    return [px[y * ART_SIZE:(y + 1) * ART_SIZE] for y in range(ART_SIZE)]


def fetch_art(url):
    """Download album art and return ART_SIZE rows of (r, g, b), or None."""
    if not url:
        return None
    try:
        from io import BytesIO
        from PIL import Image
        req = urllib.request.Request(url, headers={"User-Agent": "led-matrix"})
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            raw = resp.read()
        return prep_art(Image.open(BytesIO(raw)))
    except Exception:
        return None


def demo_art():
    """Procedural rainbow swirl so the disk works with no network/Pillow."""
    rows = []
    for y in range(ART_SIZE):
        row = []
        for x in range(ART_SIZE):
            u = x / (ART_SIZE - 1) * 2 - 1
            v = y / (ART_SIZE - 1) * 2 - 1
            ang = math.atan2(v, u)
            dist = math.hypot(u, v)
            hue = (ang / (2 * math.pi) + dist * 0.35) % 1.0
            r, g, b = colorsys.hsv_to_rgb(hue, 0.8, 0.9)
            row.append((int(r * 255), int(g * 255), int(b * 255)))
        rows.append(row)
    return rows


# ─── disk renderer ───────────────────────────────────────────────────────────
# The disk is precomputed as DISK_FRAMES pixel lists: the album art rotates
# underneath while the specular gleam and rim stay fixed in screen space,
# which is what makes it read as a glossy spinning CD.

SUBSAMPLES = ((-0.25, -0.25), (0.25, -0.25), (-0.25, 0.25), (0.25, 0.25))


def build_geometry():
    art_pixels = []   # (x, y, shade, [(dx, dy) per subsample])
    fixed_pixels = [] # (x, y, r, g, b) — hub ring, drawn every frame as-is
    for y in range(ROWS):
        for x in range(COLS):
            dx = x - DISK_CX
            dy = y - DISK_CY
            dist = math.hypot(dx, dy)
            if dist > DISK_R:
                continue
            if dist <= HOLE_R:
                continue  # spindle hole: background shows through
            if dist <= HUB_R:
                lum = 88 if int(dist * 2) % 2 == 0 else 66
                fixed_pixels.append((x, y, lum, lum + 4, lum + 10))
                continue
            # Fixed specular gleam across the face, stronger near the rim.
            ang = math.atan2(dy, dx)
            s = math.cos(2.0 * (ang - 0.9))
            gleam = 0.55 * (s ** 3) * (dist / DISK_R) ** 1.5 if s > 0 else 0.0
            shade = 1.0 + gleam
            if dist > DISK_R - 1.0:   # dark outer rim
                shade *= 0.45
            elif dist > DISK_R - 1.8:
                shade *= 0.8
            subs = [(dx + ox, dy + oy) for ox, oy in SUBSAMPLES]
            art_pixels.append((x, y, shade, subs))
    return art_pixels, fixed_pixels


GEOM_ART, GEOM_FIXED = build_geometry()


def build_disk_frames(art):
    """Precompute the rotating disk as DISK_FRAMES lists of (x, y, r, g, b)."""
    hi = ART_SIZE - 1
    frames = []
    for k in range(DISK_FRAMES):
        a = 2 * math.pi * k / DISK_FRAMES
        ca, sa = math.cos(a), math.sin(a)
        pts = list(GEOM_FIXED)
        for x, y, shade, subs in GEOM_ART:
            r = g = b = 0
            for dx, dy in subs:
                u = (dx * ca + dy * sa) / DISK_R
                v = (-dx * sa + dy * ca) / DISK_R
                ax = int((u * 0.5 + 0.5) * hi + 0.5)
                ay = int((v * 0.5 + 0.5) * hi + 0.5)
                sr, sg, sb = art[min(max(ay, 0), hi)][min(max(ax, 0), hi)]
                r += sr
                g += sg
                b += sb
            pts.append((
                x, y,
                min(255, int(r / 4 * shade)),
                min(255, int(g / 4 * shade)),
                min(255, int(b / 4 * shade)),
            ))
        frames.append(pts)
    return frames


# ─── shared state (poll thread → render loop) ────────────────────────────────

class State:
    def __init__(self):
        self.lock = threading.Lock()
        self.frames = build_disk_frames(demo_art())
        self.track_id = None
        self.title = "SPOTIFY"
        self.artist = "connecting..." if CONFIG else "run spotify_auth.py"
        self.playing = CONFIG is None  # demo disk spins until we connect
        self.has_track = False
        self.progress_ms = 0
        self.duration_ms = 0
        self.fetched_at = time.monotonic()


def spotify_worker(client, state):
    """Poll Spotify forever; on track change fetch art and rebuild frames."""
    backoff = POLL_SECONDS
    while True:
        try:
            now = client.currently_playing()
            backoff = POLL_SECONDS
        except Exception:
            backoff = min(backoff * 2, 60)
            with state.lock:
                if not state.has_track:
                    state.title = "SPOTIFY"
                    state.artist = "no connection"
                    state.playing = False
            time.sleep(backoff)
            continue

        if now is None:
            with state.lock:
                state.playing = False
                if not state.has_track:
                    state.title = "Not playing"
                    state.artist = "open Spotify"
        else:
            frames = None
            if now["id"] != state.track_id:
                art = fetch_art(now["art_url"]) or demo_art()
                frames = build_disk_frames(art)  # heavy — done off the render loop
            with state.lock:
                if frames is not None:
                    state.frames = frames
                    state.track_id = now["id"]
                state.title = now["title"]
                state.artist = now["artist"]
                state.playing = now["playing"]
                state.has_track = True
                state.progress_ms = now["progress_ms"]
                state.duration_ms = now["duration_ms"]
                state.fetched_at = time.monotonic()
        time.sleep(backoff)


# ─── drawing helpers ─────────────────────────────────────────────────────────

def text_width(font, text):
    return sum(font.CharacterWidth(ord(ch)) for ch in text)


def draw_scrolling_text(canvas, font, y, color, text, t):
    """Draw text in the right zone; scroll with wraparound when too wide."""
    w = text_width(font, text)
    if w <= TXT_W:
        graphics.DrawText(canvas, font, TXT_X0 + (TXT_W - w) // 2, y, color, text)
        return
    span = w + SCROLL_GAP
    off = int(t * SCROLL_PX_PER_S) % span
    graphics.DrawText(canvas, font, TXT_X0 - off, y, color, text)
    graphics.DrawText(canvas, font, TXT_X0 - off + span, y, color, text)


def fmt_time(ms):
    s = max(0, int(ms / 1000))
    return "%d:%02d" % (s // 60, s % 60)


def draw_frame(canvas, state_snapshot, disk_pts, t):
    (title, artist, playing, has_track, progress_ms, duration_ms) = state_snapshot
    canvas.Clear()

    # Text first: scrolling bleeds left of the zone, so black out that strip
    # and then draw the disk on top of it.
    white = graphics.Color(230, 230, 235)
    gray = graphics.Color(120, 120, 130)
    draw_scrolling_text(canvas, FONT_TITLE, 8, white, title, t)
    draw_scrolling_text(canvas, FONT_SMALL, 16, gray, artist, t + 1.7)
    for y in range(0, 18):
        for x in range(0, TXT_X0):
            canvas.SetPixel(x, y, 0, 0, 0)

    for x, y, r, g, b in disk_pts:
        canvas.SetPixel(x, y, r, g, b)

    if has_track and duration_ms > 0:
        frac = min(1.0, progress_ms / duration_ms)
        bar_w = TXT_W - 1
        fill = int(frac * bar_w)
        fr, fg, fb = SPOTIFY_GREEN if playing else (150, 150, 60)
        for i in range(bar_w):
            on = i <= fill
            for yy in (20, 21):
                if on:
                    canvas.SetPixel(TXT_X0 + i, yy, fr, fg, fb)
                else:
                    canvas.SetPixel(TXT_X0 + i, yy, 28, 28, 32)
        elapsed = fmt_time(progress_ms)
        total = fmt_time(duration_ms)
        # Elapsed takes the bar's color so the two times read as separate
        # values — there's only a 1px gap between them at this size.
        graphics.DrawText(
            canvas, FONT_SMALL, TXT_X0, 30, graphics.Color(fr, fg, fb), elapsed
        )
        graphics.DrawText(
            canvas, FONT_SMALL, COLS - text_width(FONT_SMALL, total), 30, gray, total
        )


# ─── main loop ───────────────────────────────────────────────────────────────

def main():
    # Config and fonts are already loaded at import time — before this
    # constructor drops privileges to user "daemon".
    opts = RGBMatrixOptions()
    opts.rows = ROWS
    opts.cols = COLS
    opts.brightness = read_initial_brightness()
    matrix = RGBMatrix(options=opts)
    canvas = matrix.CreateFrameCanvas()

    state = State()
    if CONFIG:
        try:
            thread = threading.Thread(
                target=spotify_worker, args=(SpotifyClient(CONFIG), state), daemon=True
            )
            thread.start()
        except RuntimeError:
            pass  # no threads (browser preview) — demo disk keeps spinning

    rot = 0.0
    start = time.monotonic()
    prev = start
    next_frame_time = start
    try:
        while True:
            now = time.monotonic()
            dt = now - prev
            prev = now
            t = now - start

            apply_live_brightness(matrix)

            with state.lock:
                playing = state.playing
                progress = state.progress_ms
                if playing and state.has_track:
                    progress += int((now - state.fetched_at) * 1000)
                    progress = min(progress, state.duration_ms)
                snapshot = (
                    state.title,
                    state.artist,
                    playing,
                    state.has_track,
                    progress,
                    state.duration_ms,
                )
                frames = state.frames

            if playing:
                rot = (rot + dt / SPIN_SECONDS) % 1.0
            disk_pts = frames[int(rot * DISK_FRAMES) % DISK_FRAMES]

            draw_frame(canvas, snapshot, disk_pts, t)
            canvas = matrix.SwapOnVSync(canvas)

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
