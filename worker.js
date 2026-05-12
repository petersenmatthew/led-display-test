// Web Worker that runs user Python via Pyodide and exposes a JS-backed
// `rgbmatrix` module mirroring hzeller's rpi-rgb-led-matrix Python API.
// Scripts written here run unchanged on a real Raspberry Pi.

const PYODIDE_VERSION = "0.26.4";
const PYODIDE_BASE = `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/`;
const FONT_BASE = "./fonts/";
const FONT_FILES = ["4x6.bdf", "5x7.bdf", "5x8.bdf", "6x9.bdf", "6x10.bdf", "6x12.bdf", "6x13.bdf", "7x13.bdf", "7x14.bdf", "8x13.bdf", "9x15.bdf", "9x18.bdf", "10x20.bdf", "tom-thumb.bdf"];

importScripts(PYODIDE_BASE + "pyodide.js");

// ─── BDF parser ──────────────────────────────────────────────────────────────
function parseBDF(text) {
  const lines = text.split(/\r?\n/);
  const font = { bbox: { w: 0, h: 0, x: 0, y: 0 }, ascent: 0, descent: 0, glyphs: {} };
  let i = 0;
  while (i < lines.length) {
    const line = lines[i++].trim();
    if (line.startsWith("FONTBOUNDINGBOX")) {
      const [, w, h, x, y] = line.split(/\s+/);
      font.bbox = { w: +w, h: +h, x: +x, y: +y };
    } else if (line.startsWith("FONT_ASCENT")) {
      font.ascent = +line.split(/\s+/)[1];
    } else if (line.startsWith("FONT_DESCENT")) {
      font.descent = +line.split(/\s+/)[1];
    } else if (line.startsWith("STARTCHAR")) {
      const glyph = { dwidth: 0, bbx: { w: 0, h: 0, x: 0, y: 0 }, rows: [] };
      let cp = -1;
      while (i < lines.length) {
        const gl = lines[i++].trim();
        if (gl.startsWith("ENCODING")) cp = +gl.split(/\s+/)[1];
        else if (gl.startsWith("DWIDTH")) glyph.dwidth = +gl.split(/\s+/)[1];
        else if (gl.startsWith("BBX")) {
          const [, w, h, x, y] = gl.split(/\s+/);
          glyph.bbx = { w: +w, h: +h, x: +x, y: +y };
        } else if (gl === "BITMAP") {
          for (let r = 0; r < glyph.bbx.h; r++) {
            const hex = (lines[i++] || "").trim();
            glyph.rows.push({ val: BigInt("0x" + (hex || "0")), bits: hex.length * 4 });
          }
        } else if (gl === "ENDCHAR") {
          if (cp >= 0) font.glyphs[cp] = glyph;
          break;
        }
      }
    }
  }
  return font;
}

// ─── Font registry ───────────────────────────────────────────────────────────
const FONTS = {}; // basename → parsed font

async function preloadFonts() {
  await Promise.all(FONT_FILES.map(async (name) => {
    try {
      const r = await fetch(FONT_BASE + name);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      FONTS[name] = parseBDF(await r.text());
    } catch (e) {
      postMessage({ type: "stderr", s: `[font] failed to load ${name}: ${e}\n` });
    }
  }));
}

// ─── rgbmatrix shim ──────────────────────────────────────────────────────────
const COLS = 64;
const ROWS = 32;

let frameCount = 0;
function postFrame(buf) {
  // Copy so the worker keeps its own buffer; main thread gets a fresh slice.
  const copy = new Uint8Array(buf);
  postMessage({ type: "frame", buf: copy }, [copy.buffer]);
  frameCount++;
}

class _RGBMatrixOptions {
  constructor() {
    this.rows = 32;
    this.cols = 64;
    this.chain_length = 1;
    this.parallel = 1;
    this.hardware_mapping = "regular";
    this.brightness = 100;
    this.pwm_bits = 11;
    this.gpio_slowdown = 1;
    this.disable_hardware_pulsing = false;
    this.drop_privileges = true;
    this.pixel_mapper_config = "";
  }
}

class _Canvas {
  constructor(width, height) {
    this.width = width;
    this.height = height;
    this.buf = new Uint8Array(width * height * 3);
  }
  SetPixel(x, y, r, g, b) {
    x |= 0; y |= 0;
    if (x < 0 || x >= this.width || y < 0 || y >= this.height) return;
    const i = (y * this.width + x) * 3;
    this.buf[i] = r & 0xff;
    this.buf[i + 1] = g & 0xff;
    this.buf[i + 2] = b & 0xff;
  }
  Clear() { this.buf.fill(0); }
  Fill(r, g, b) {
    for (let i = 0; i < this.buf.length; i += 3) {
      this.buf[i] = r & 0xff;
      this.buf[i + 1] = g & 0xff;
      this.buf[i + 2] = b & 0xff;
    }
  }
  SetImage(img, ox = 0, oy = 0) {
    // Best-effort Pillow support: expect img.tobytes() returning RGB bytes,
    // plus img.size = (w, h). Works with `from PIL import Image`.
    if (!img) return;
    let bytes, w, h;
    if (typeof img.tobytes === "function") {
      bytes = img.tobytes();
      [w, h] = img.size;
    } else if (img.data && img.width && img.height) {
      bytes = img.data; w = img.width; h = img.height;
    } else return;
    for (let y = 0; y < h; y++) {
      for (let x = 0; x < w; x++) {
        const j = (y * w + x) * 3;
        this.SetPixel(ox + x, oy + y, bytes[j], bytes[j + 1], bytes[j + 2]);
      }
    }
  }
}

class _FrameCanvas extends _Canvas {}

class _RGBMatrix extends _Canvas {
  constructor({ options } = {}) {
    const opts = options || new _RGBMatrixOptions();
    super(opts.cols * opts.chain_length, opts.rows * opts.parallel);
    this.brightness = opts.brightness;
  }
  CreateFrameCanvas() { return new _FrameCanvas(this.width, this.height); }
  SwapOnVSync(fc) {
    postFrame(fc.buf);
    return fc; // hzeller returns the previous buffer; we hand back the same one.
  }
}

// graphics submodule ---------------------------------------------------------

function _Color(r, g, b) { return { r: r & 0xff, g: g & 0xff, b: b & 0xff }; }

class _Font {
  constructor() { this.bdf = null; this._path = ""; }
  LoadFont(path) {
    this._path = path;
    const base = String(path).split("/").pop();
    const f = FONTS[base];
    if (!f) throw new Error(`Font not found: ${base}. Available: ${Object.keys(FONTS).join(", ")}`);
    this.bdf = f;
  }
  get height() { return this.bdf ? this.bdf.bbox.h : 0; }
  get baseline() { return this.bdf ? this.bdf.ascent : 0; }
  CharacterWidth(cp) {
    const g = this.bdf && this.bdf.glyphs[cp];
    return g ? g.dwidth : 0;
  }
}

function _drawGlyph(canvas, glyph, px, py, color) {
  // BDF: bbx (w h xo yo). yo is offset of bbx bottom-left from baseline (often negative).
  // Top row of bbx in canvas coords = py - yo - h + 1.
  const { w, h, x: xo, y: yo } = glyph.bbx;
  const left = px + xo;
  const top = py - yo - h + 1;
  for (let r = 0; r < h; r++) {
    const row = glyph.rows[r];
    if (!row) continue;
    const { val, bits } = row;
    for (let c = 0; c < w; c++) {
      const bit = (val >> BigInt(bits - 1 - c)) & 1n;
      if (bit === 1n) canvas.SetPixel(left + c, top + r, color.r, color.g, color.b);
    }
  }
}

function _DrawText(canvas, font, x, y, color, text) {
  if (!font.bdf) throw new Error("Font not loaded — call font.LoadFont(...) first.");
  const str = String(text);
  let cx = x | 0;
  const y0 = y | 0;
  let drawn = 0;
  for (const ch of str) {
    const cp = ch.codePointAt(0);
    const g = font.bdf.glyphs[cp];
    if (g) {
      _drawGlyph(canvas, g, cx, y0, color);
      cx += g.dwidth;
      drawn += g.dwidth;
    } else {
      // Unknown glyph: advance by the font's default width.
      const fallback = font.bdf.glyphs[32] ? font.bdf.glyphs[32].dwidth : font.bdf.bbox.w;
      cx += fallback;
      drawn += fallback;
    }
  }
  return drawn;
}

function _DrawLine(canvas, x0, y0, x1, y1, color) {
  x0 |= 0; y0 |= 0; x1 |= 0; y1 |= 0;
  const dx = Math.abs(x1 - x0), sx = x0 < x1 ? 1 : -1;
  const dy = -Math.abs(y1 - y0), sy = y0 < y1 ? 1 : -1;
  let err = dx + dy;
  for (;;) {
    canvas.SetPixel(x0, y0, color.r, color.g, color.b);
    if (x0 === x1 && y0 === y1) break;
    const e2 = 2 * err;
    if (e2 >= dy) { err += dy; x0 += sx; }
    if (e2 <= dx) { err += dx; y0 += sy; }
  }
}

function _DrawCircle(canvas, cx, cy, radius, color) {
  // Midpoint circle algorithm (outline).
  let x = radius | 0, y = 0, err = 0;
  while (x >= y) {
    const pts = [[ x, y], [ y, x], [-y, x], [-x, y], [-x,-y], [-y,-x], [ y,-x], [ x,-y]];
    for (const [dx, dy] of pts) canvas.SetPixel(cx + dx, cy + dy, color.r, color.g, color.b);
    y++;
    if (err <= 0) { err += 2 * y + 1; }
    if (err > 0)  { x--; err -= 2 * x + 1; }
  }
}

// Pyodide calls JS callables without the `new` operator, which ES6 classes
// reject. Wrap each class in a plain function so `Foo(...)` from Python works.
const graphics = {
  Color: _Color,
  Font: function Font() { return new _Font(); },
  DrawText: _DrawText,
  DrawLine: _DrawLine,
  DrawCircle: _DrawCircle,
};

const rgbmatrixModule = {
  RGBMatrix: function (kwargs) { return new _RGBMatrix(kwargs); },
  RGBMatrixOptions: function () { return new _RGBMatrixOptions(); },
  FrameCanvas: function (w, h) { return new _FrameCanvas(w, h); },
  graphics,
};

// ─── Pyodide bootstrap ───────────────────────────────────────────────────────
let pyodide;
let initPromise = (async () => {
  postMessage({ type: "status", s: "loading pyodide…" });
  pyodide = await loadPyodide({ indexURL: PYODIDE_BASE });
  pyodide.setStdout({ batched: (s) => postMessage({ type: "stdout", s: s + "\n" }) });
  pyodide.setStderr({ batched: (s) => postMessage({ type: "stderr", s: s + "\n" }) });
  postMessage({ type: "status", s: "loading fonts…" });
  await preloadFonts();
  pyodide.registerJsModule("rgbmatrix", rgbmatrixModule);
  postMessage({ type: "ready" });
})().catch((e) => {
  postMessage({ type: "stderr", s: `[init] ${e}\n` });
});

// ─── Message handler ─────────────────────────────────────────────────────────
onmessage = async (e) => {
  const msg = e.data;
  if (msg.type === "run") {
    await initPromise;
    if (!pyodide) return;
    postMessage({ type: "status", s: "running" });
    try {
      await pyodide.runPythonAsync(msg.code);
      postMessage({ type: "status", s: "finished" });
    } catch (err) {
      postMessage({ type: "stderr", s: String(err.message || err) + "\n" });
      postMessage({ type: "status", s: "error" });
    }
  }
};
