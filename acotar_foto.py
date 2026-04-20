#!/usr/bin/env python3
"""Agregar cotas de medidas a una imagen de producto (estilo plano técnico).

Dibuja líneas de extensión, líneas de cota con flechitas y texto de medida
sobre un canvas expandido para no pisar el sujeto.

Uso:
    python3 acotar_foto.py <imagen> --ancho 45 --alto 60 [--unidad cm] [--padding N]

Ejemplos:
    python3 acotar_foto.py producto.png --ancho 45 --alto 60
    python3 acotar_foto.py producto.png --ancho 30 --unidad mm
    python3 acotar_foto.py producto.png --alto 12 --unidad '"' --padding 60
    python3 acotar_foto.py producto.png --ancho 45 --alto 60 --output /tmp/out.png
"""
import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

FONT_CANDIDATES = [
    "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/liberation-sans-fonts/LiberationSans-Bold.ttf",
    "/usr/share/fonts/google-noto-vf/NotoSans[wght].ttf",
    "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans.ttf",
]

LINE_COLOR = (0, 40, 120)
LINE_WIDTH = 2
ARROW_SIZE = 14
EXT_OVERSHOOT = 8
DEFAULT_PADDING = 50
LABEL_BG = (255, 255, 255, 230)
LABEL_PAD_X = 10
LABEL_PAD_Y = 4
LABEL_BORDER = (0, 40, 120, 180)


def find_font(size: int) -> ImageFont.FreeTypeFont:
    for path in FONT_CANDIDATES:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def detect_bbox(img: Image.Image) -> tuple[int, int, int, int]:
    """Detecta bounding box del sujeto. Retorna (left, top, right, bottom)."""
    arr = np.array(img)
    if arr.shape[2] == 4:
        mask = arr[..., 3] > 0
    else:
        gray = arr[..., :3].mean(axis=2)
        mask = gray < 240
    ys, xs = np.where(mask)
    if len(xs) == 0:
        h, w = arr.shape[:2]
        return 0, 0, w, h
    return int(xs.min()), int(ys.min()), int(xs.max() + 1), int(ys.max() + 1)


def draw_arrow(draw: ImageDraw.Draw, tip: tuple[int, int], direction: str):
    """Dibuja un triángulo sólido pequeño apuntando en direction (up/down/left/right)."""
    tx, ty = tip
    s = ARROW_SIZE
    if direction == "left":
        pts = [(tx, ty), (tx + s, ty - s // 2), (tx + s, ty + s // 2)]
    elif direction == "right":
        pts = [(tx, ty), (tx - s, ty - s // 2), (tx - s, ty + s // 2)]
    elif direction == "up":
        pts = [(tx, ty), (tx - s // 2, ty + s), (tx + s // 2, ty + s)]
    else:  # down
        pts = [(tx, ty), (tx - s // 2, ty - s), (tx + s // 2, ty - s)]
    draw.polygon(pts, fill=LINE_COLOR)


def draw_label(draw: ImageDraw.Draw, center: tuple[int, int], text: str,
               font: ImageFont.FreeTypeFont):
    """Dibuja el texto de medida con fondo semi-transparente y borde."""
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    cx, cy = center
    x = cx - tw // 2
    y = cy - th // 2
    rx0 = x - LABEL_PAD_X
    ry0 = y - LABEL_PAD_Y
    rx1 = x + tw + LABEL_PAD_X
    ry1 = y + th + LABEL_PAD_Y
    draw.rounded_rectangle((rx0, ry0, rx1, ry1), radius=4, fill=LABEL_BG, outline=LABEL_BORDER, width=1)
    draw.text((x, y), text, fill=LINE_COLOR, font=font)


def format_measure(value: float) -> str:
    return f"{value:g}"


def acotar(entrada: Path, salida: Path, ancho: float | None, alto: float | None,
           unidad: str, padding: int):
    img = Image.open(entrada).convert("RGBA")
    orig_w, orig_h = img.size
    left, top, right, bottom = detect_bbox(img)
    subj_w = right - left
    subj_h = bottom - top
    print(f"Imagen: {orig_w}x{orig_h}  |  Sujeto bbox: ({left},{top})-({right},{bottom})  [{subj_w}x{subj_h}]")

    cota_zone = padding + 50
    expand_bottom = cota_zone if ancho else 0
    expand_right = cota_zone if alto else 0

    canvas_w = orig_w + expand_right
    canvas_h = orig_h + expand_bottom
    canvas = Image.new("RGBA", (canvas_w, canvas_h), (255, 255, 255, 0))
    canvas.paste(img, (0, 0))

    draw = ImageDraw.Draw(canvas)
    font_size = max(20, min(orig_w, orig_h) // 22)
    font = find_font(font_size)

    dim_offset = padding + 20

    if ancho:
        label = f"{format_measure(ancho)} {unidad}"
        cy = bottom + dim_offset
        # extension lines
        draw.line([(left, bottom + 4), (left, cy + EXT_OVERSHOOT)], fill=LINE_COLOR, width=LINE_WIDTH)
        draw.line([(right - 1, bottom + 4), (right - 1, cy + EXT_OVERSHOOT)], fill=LINE_COLOR, width=LINE_WIDTH)
        # dimension line
        draw.line([(left, cy), (right - 1, cy)], fill=LINE_COLOR, width=LINE_WIDTH)
        # arrows
        draw_arrow(draw, (left, cy), "left")
        draw_arrow(draw, (right - 1, cy), "right")
        # label
        draw_label(draw, ((left + right) // 2, cy), label, font)
        print(f"Cota ancho: {label}")

    if alto:
        label = f"{format_measure(alto)} {unidad}"
        cx = right + dim_offset
        # extension lines
        draw.line([(right + 4, top), (cx + EXT_OVERSHOOT, top)], fill=LINE_COLOR, width=LINE_WIDTH)
        draw.line([(right + 4, bottom - 1), (cx + EXT_OVERSHOOT, bottom - 1)], fill=LINE_COLOR, width=LINE_WIDTH)
        # dimension line
        draw.line([(cx, top), (cx, bottom - 1)], fill=LINE_COLOR, width=LINE_WIDTH)
        # arrows
        draw_arrow(draw, (cx, top), "up")
        draw_arrow(draw, (cx, bottom - 1), "down")
        # label
        draw_label(draw, (cx, (top + bottom) // 2), label, font)
        print(f"Cota alto: {label}")

    canvas.save(salida)
    print(f"Canvas: {canvas_w}x{canvas_h}  |  Padding: {padding}px")
    print(f"✓ {salida}")


def main():
    p = argparse.ArgumentParser(
        description="Agregar cotas de medidas a una imagen de producto.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("imagen", type=Path)
    p.add_argument("--ancho", type=float, default=None, help="Ancho real del producto")
    p.add_argument("--alto", type=float, default=None, help="Alto real del producto")
    p.add_argument("--unidad", default="cm", help="Unidad de medida (default: cm)")
    p.add_argument("--padding", type=int, default=DEFAULT_PADDING, help=f"Separación cotas-sujeto en px (default {DEFAULT_PADDING})")
    p.add_argument("--output", type=Path, default=None)
    args = p.parse_args()

    if not args.ancho and not args.alto:
        print("Error: pasá al menos --ancho o --alto", file=sys.stderr)
        sys.exit(1)

    entrada = args.imagen.resolve()
    if not entrada.exists():
        print(f"No existe: {entrada}", file=sys.stderr)
        sys.exit(1)
    salida = args.output.resolve() if args.output else entrada.with_name(f"{entrada.stem}_acotada.png")

    acotar(entrada, salida, args.ancho, args.alto, args.unidad, args.padding)


if __name__ == "__main__":
    main()
