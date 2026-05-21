#!/usr/bin/env python3
"""Render rgbmatrix LED scripts to a PNG without physical hardware."""

from __future__ import annotations

import argparse
import importlib.util
import inspect
import sys
import types
from pathlib import Path

try:
    from PIL import Image
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Pillow is required: python3 -m pip install pillow") from exc


class Color(tuple):
    def __new__(cls, r, g, b):
        return super().__new__(cls, (int(r) & 0xFF, int(g) & 0xFF, int(b) & 0xFF))

    @property
    def r(self):
        return self[0]

    @property
    def g(self):
        return self[1]

    @property
    def b(self):
        return self[2]


class Font:
    def __init__(self):
        self.path = None

    def LoadFont(self, path):
        self.path = path


def _color_tuple(color):
    if isinstance(color, tuple):
        return int(color[0]), int(color[1]), int(color[2])
    return int(color.r), int(color.g), int(color.b)


GLYPHS_3X5 = {
    "0": ("111", "101", "101", "101", "111"),
    "1": ("010", "110", "010", "010", "111"),
    "2": ("111", "001", "111", "100", "111"),
    "3": ("111", "001", "111", "001", "111"),
    "4": ("101", "101", "111", "001", "001"),
    "5": ("111", "100", "111", "001", "111"),
    "6": ("111", "100", "111", "101", "111"),
    "7": ("111", "001", "010", "010", "010"),
    "8": ("111", "101", "111", "101", "111"),
    "9": ("111", "101", "111", "001", "111"),
    "A": ("111", "101", "111", "101", "101"),
    "B": ("110", "101", "110", "101", "110"),
    "C": ("111", "100", "100", "100", "111"),
    "D": ("110", "101", "101", "101", "110"),
    "E": ("111", "100", "110", "100", "111"),
    "F": ("111", "100", "110", "100", "100"),
    "G": ("111", "100", "101", "101", "111"),
    "H": ("101", "101", "111", "101", "101"),
    "I": ("111", "010", "010", "010", "111"),
    "J": ("001", "001", "001", "101", "111"),
    "K": ("101", "101", "110", "101", "101"),
    "L": ("100", "100", "100", "100", "111"),
    "M": ("101", "111", "111", "101", "101"),
    "N": ("101", "111", "111", "111", "101"),
    "O": ("111", "101", "101", "101", "111"),
    "P": ("111", "101", "111", "100", "100"),
    "Q": ("111", "101", "101", "111", "001"),
    "R": ("111", "101", "111", "110", "101"),
    "S": ("111", "100", "111", "001", "111"),
    "T": ("111", "010", "010", "010", "010"),
    "U": ("101", "101", "101", "101", "111"),
    "V": ("101", "101", "101", "101", "010"),
    "W": ("101", "101", "111", "111", "101"),
    "X": ("101", "101", "010", "101", "101"),
    "Y": ("101", "101", "010", "010", "010"),
    "Z": ("111", "001", "010", "100", "111"),
    "-": ("000", "000", "111", "000", "000"),
    "/": ("001", "001", "010", "100", "100"),
    ".": ("000", "000", "000", "000", "010"),
    ":": ("000", "010", "000", "010", "000"),
}


def DrawText(canvas, font, x, y, color, text):
    r, g, b = _color_tuple(color)
    width = 0
    for ch in str(text):
        glyph = GLYPHS_3X5.get(ch.upper())
        if glyph:
            for row, pattern in enumerate(glyph):
                for col, bit in enumerate(pattern):
                    if bit == "1":
                        canvas.SetPixel(x + width + col, y - 4 + row, r, g, b)
        width += 4
    return width


def DrawLine(canvas, x0, y0, x1, y1, color):
    r, g, b = _color_tuple(color)
    dx = abs(x1 - x0)
    sx = 1 if x0 < x1 else -1
    dy = -abs(y1 - y0)
    sy = 1 if y0 < y1 else -1
    err = dx + dy

    while True:
        canvas.SetPixel(x0, y0, r, g, b)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


class RGBMatrixOptions:
    def __init__(self):
        self.rows = 32
        self.cols = 64
        self.chain_length = 1
        self.parallel = 1
        self.hardware_mapping = "regular"
        self.brightness = 100
        self.pwm_bits = 11
        self.gpio_slowdown = 1


class Canvas:
    def __init__(self, width=64, height=32):
        self.width = int(width)
        self.height = int(height)
        self.pixels = {}

    def SetPixel(self, x, y, r, g, b):
        x = int(x)
        y = int(y)
        if 0 <= x < self.width and 0 <= y < self.height:
            self.pixels[(x, y)] = (int(r) & 0xFF, int(g) & 0xFF, int(b) & 0xFF)

    def Clear(self):
        self.pixels.clear()

    def Fill(self, r, g, b):
        col = (int(r) & 0xFF, int(g) & 0xFF, int(b) & 0xFF)
        for y in range(self.height):
            for x in range(self.width):
                self.pixels[(x, y)] = col


class RGBMatrix(Canvas):
    def __init__(self, options=None, **kwargs):
        opts = options or kwargs.get("options") or RGBMatrixOptions()
        width = opts.cols * getattr(opts, "chain_length", 1)
        height = opts.rows * getattr(opts, "parallel", 1)
        super().__init__(width, height)
        self.last_frame = None

    def CreateFrameCanvas(self):
        return Canvas(self.width, self.height)

    def SwapOnVSync(self, canvas):
        self.last_frame = canvas
        return canvas


def install_rgbmatrix_stub():
    graphics = types.ModuleType("rgbmatrix.graphics")
    graphics.Font = Font
    graphics.Color = Color
    graphics.DrawText = DrawText
    graphics.DrawLine = DrawLine

    rgbmatrix = types.ModuleType("rgbmatrix")
    rgbmatrix.RGBMatrix = RGBMatrix
    rgbmatrix.RGBMatrixOptions = RGBMatrixOptions
    rgbmatrix.FrameCanvas = Canvas
    rgbmatrix.graphics = graphics

    sys.modules["rgbmatrix"] = rgbmatrix
    sys.modules["rgbmatrix.graphics"] = graphics


def import_target(path):
    install_rgbmatrix_stub()
    script = Path(path).resolve()
    sys.path.insert(0, str(script.parent))
    spec = importlib.util.spec_from_file_location(script.stem.replace("-", "_"), script)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def infer_size(module, width, height):
    if width and height:
        return width, height
    if hasattr(module, "W") and hasattr(module, "H"):
        return int(module.W), int(module.H)

    cols = int(getattr(module, "COLS", 64))
    rows = int(getattr(module, "ROWS", 32))
    chain = int(getattr(module, "CHAIN_LENGTH", 1))
    parallel = int(getattr(module, "PARALLEL", 1))
    return width or cols * chain, height or rows * parallel


def render_function(module, function_name, frame, width, height):
    canvas = Canvas(width, height)
    fn = getattr(module, function_name)
    signature = inspect.signature(fn)
    positional = [
        param
        for param in signature.parameters.values()
        if param.kind
        in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
    ]

    if len(positional) >= 2:
        fn(canvas, frame)
    elif len(positional) == 1:
        fn(canvas)
    else:
        fn()

    return canvas


def canvas_to_png(canvas, output, scale):
    img = Image.new("RGB", (canvas.width, canvas.height), (0, 0, 0))
    for (x, y), col in canvas.pixels.items():
        img.putpixel((x, y), col)

    if scale != 1:
        img = img.resize((canvas.width * scale, canvas.height * scale), Image.Resampling.NEAREST)

    img.save(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("script", help="Path to the rgbmatrix Python script")
    parser.add_argument("--function", required=True, help="Draw function to call, e.g. draw_night")
    parser.add_argument("--frame", type=int, default=0, help="Frame number passed to the draw function")
    parser.add_argument("--width", type=int)
    parser.add_argument("--height", type=int)
    parser.add_argument("--scale", type=int, default=10)
    parser.add_argument("--output", default="/private/tmp/led-matrix-preview.png")
    args = parser.parse_args()

    module = import_target(args.script)
    width, height = infer_size(module, args.width, args.height)
    canvas = render_function(module, args.function, args.frame, width, height)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas_to_png(canvas, output, args.scale)
    print(output)


if __name__ == "__main__":
    main()
