#!/usr/bin/env python3
"""Turn a 64x32 PNG into a standalone RGB matrix Python script."""

from __future__ import annotations

import argparse
import base64
from io import BytesIO
from pathlib import Path
from textwrap import dedent

from PIL import Image


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create a Raspberry Pi rgbmatrix script from a PNG."
    )
    parser.add_argument("image", help="Path to a PNG that is exactly 64x32.")
    parser.add_argument("output", help="Python script to write for the Pi.")
    parser.add_argument("--rows", type=int, default=32)
    parser.add_argument("--cols", type=int, default=64)
    parser.add_argument("--chain-length", type=int, default=1)
    parser.add_argument("--parallel", type=int, default=1)
    parser.add_argument("--gpio-slowdown", type=int, default=4)
    parser.add_argument("--brightness", type=int, default=80)
    parser.add_argument("--hardware-mapping", default="regular")
    parser.add_argument("--pwm-bits", type=int, default=11)
    return parser


def load_png_bytes(path: Path, width: int, height: int) -> bytes:
    image = Image.open(path).convert("RGB")
    if image.size != (width, height):
        raise ValueError(
            f"{path} is {image.size[0]}x{image.size[1]}, expected {width}x{height}."
        )

    png_bytes = BytesIO()
    image.save(png_bytes, format="PNG")
    return png_bytes.getvalue()


def make_script(args: argparse.Namespace, encoded_png: str) -> str:
    return dedent(
        f"""\
        #!/usr/bin/env python3
        \"\"\"Display embedded PNG art on an RGB LED matrix.\"\"\"

        import base64
        import time
        from io import BytesIO

        from PIL import Image
        from rgbmatrix import RGBMatrix, RGBMatrixOptions


        ROWS = {args.rows}
        COLS = {args.cols}
        CHAIN_LENGTH = {args.chain_length}
        PARALLEL = {args.parallel}
        GPIO_SLOWDOWN = {args.gpio_slowdown}
        BRIGHTNESS = {args.brightness}
        HARDWARE_MAPPING = {args.hardware_mapping!r}
        PWM_BITS = {args.pwm_bits}

        PNG_BASE64 = \"\"\"{encoded_png}\"\"\"


        def create_matrix():
            options = RGBMatrixOptions()
            options.rows = ROWS
            options.cols = COLS
            options.chain_length = CHAIN_LENGTH
            options.parallel = PARALLEL
            options.gpio_slowdown = GPIO_SLOWDOWN
            options.brightness = BRIGHTNESS
            options.hardware_mapping = HARDWARE_MAPPING
            options.pwm_bits = PWM_BITS
            return RGBMatrix(options=options)


        def main():
            image_bytes = base64.b64decode(PNG_BASE64)
            image = Image.open(BytesIO(image_bytes)).convert("RGB")

            matrix = create_matrix()
            matrix.SetImage(image)

            print("Displaying embedded PNG. Press Ctrl+C to stop.")
            try:
                while True:
                    time.sleep(3600)
            except KeyboardInterrupt:
                matrix.Clear()


        if __name__ == "__main__":
            main()
        """
    )


def main() -> int:
    args = build_parser().parse_args()
    width = args.cols * args.chain_length
    height = args.rows * args.parallel
    image_path = Path(args.image).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()

    png_bytes = load_png_bytes(image_path, width, height)
    encoded_png = base64.b64encode(png_bytes).decode("ascii")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(make_script(args, encoded_png))
    output_path.chmod(0o755)

    print(f"Wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
