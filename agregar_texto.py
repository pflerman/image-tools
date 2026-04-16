#!/usr/bin/env python3
"""Agregar texto a una imagen con color de contraste automático y posición inteligente.

Extrae el color dominante, elige un color de texto de alto contraste (blanco o negro
según luminancia), detecta la zona con más espacio libre (menor varianza local o más
transparencia) y renderiza el texto centrado con sombra/contorno para legibilidad.

Uso:
    agregar_texto <imagen> <texto> [--position top|bottom|auto] [--size N] [--output ruta]

Ejemplos:
    agregar_texto foto.png 'Mi título'
    agregar_texto foto.png 'Oferta' --position top --size 80
    agregar_texto foto.png 'Texto largo que wrappea' --output out.png
"""
import argparse
import sys
import textwrap
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

FONT_CANDIDATES = [
    "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/liberation-sans-fonts/LiberationSans-Bold.ttf",
    "/usr/share/fonts/google-noto-vf/NotoSans[wght].ttf",
    "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans.ttf",
]


def find_font(size: int) -> ImageFont.FreeTypeFont:
    for path in FONT_CANDIDATES:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def dominant_color(img: Image.Image) -> tuple[int, int, int]:
    """Color dominante por cuantización a 8 colores."""
    small = img.convert("RGB").resize((100, 100))
    quant = small.quantize(colors=8)
    palette = quant.getpalette()
    counts = sorted(quant.getcolors(), reverse=True)
    idx = counts[0][1]
    return tuple(palette[idx * 3 : idx * 3 + 3])


def luminance(rgb: tuple[int, int, int]) -> float:
    r, g, b = [c / 255 for c in rgb]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def choose_text_color(bg_rgb: tuple[int, int, int]) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
    """Retorna (color_texto, color_contorno) de alto contraste con el fondo."""
    if luminance(bg_rgb) > 0.5:
        return (0, 0, 0), (255, 255, 255)
    return (255, 255, 255), (0, 0, 0)


def best_band(img: Image.Image) -> str:
    """Elige 'top' o 'bottom' según qué banda tiene menos detalle/sujeto."""
    arr = np.array(img.convert("RGBA"))
    h = arr.shape[0]
    band_h = h // 4

    def busyness(y0: int, y1: int) -> float:
        region = arr[y0:y1]
        if region.shape[-1] == 4:
            alpha = region[..., 3]
            # si hay mucha transparencia, es zona libre (baja busyness)
            if (alpha < 128).mean() > 0.7:
                return 0.0
        gray = region[..., :3].mean(axis=2)
        return float(gray.std())

    top_busy = busyness(0, band_h)
    bot_busy = busyness(h - band_h, h)
    return "top" if top_busy < bot_busy else "bottom"


def wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    """Wrappea el texto para que no exceda max_width."""
    words = text.split()
    if not words:
        return [text]
    lines = []
    current = words[0]
    for word in words[1:]:
        test = current + " " + word
        if font.getlength(test) <= max_width:
            current = test
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def render_text(
    img: Image.Image,
    text: str,
    position: str = "auto",
    font_size: int | None = None,
) -> Image.Image:
    W, H = img.size
    if font_size is None:
        font_size = max(24, W // 18)
    font = find_font(font_size)

    max_text_width = int(W * 0.9)
    lines = wrap_text(text, font, max_text_width)

    # medir bloque de texto
    draw_probe = ImageDraw.Draw(img)
    line_heights = []
    line_widths = []
    for line in lines:
        bbox = draw_probe.textbbox((0, 0), line, font=font)
        line_widths.append(bbox[2] - bbox[0])
        line_heights.append(bbox[3] - bbox[1])
    line_h = max(line_heights) if line_heights else font_size
    gap = int(line_h * 0.3)
    block_h = line_h * len(lines) + gap * (len(lines) - 1)
    block_w = max(line_widths) if line_widths else 0

    # posición
    if position == "auto":
        position = best_band(img)

    margin = int(H * 0.05)
    if position == "top":
        y_start = margin
    else:  # bottom
        y_start = H - margin - block_h
    x_center = W // 2

    # muestrear color de la zona donde va el texto para elegir contraste
    arr = np.array(img.convert("RGB"))
    y0 = max(0, y_start)
    y1 = min(H, y_start + block_h)
    region_color = tuple(arr[y0:y1].mean(axis=(0, 1)).astype(int))
    text_color, stroke_color = choose_text_color(region_color)

    # renderizar con contorno grueso para legibilidad siempre
    stroke_w = max(2, font_size // 20)
    out = img.convert("RGBA").copy()
    draw = ImageDraw.Draw(out)
    y = y_start
    for line, lw in zip(lines, line_widths):
        x = x_center - lw // 2
        draw.text(
            (x, y), line, font=font, fill=text_color,
            stroke_width=stroke_w, stroke_fill=stroke_color,
        )
        y += line_h + gap

    dom = dominant_color(img)
    print(f"Color dominante: RGB{dom}  |  Texto: RGB{text_color}  |  Contorno: RGB{stroke_color}")
    print(f"Posición: {position}  |  Fuente: {font_size}px  |  Líneas: {len(lines)}")
    return out


def main():
    p = argparse.ArgumentParser(description="Agregar texto a una imagen con contraste automático.")
    p.add_argument("imagen", type=Path)
    p.add_argument("texto")
    p.add_argument("--position", choices=["top", "bottom", "auto"], default="auto")
    p.add_argument("--size", type=int, default=None, help="Tamaño de fuente en px")
    p.add_argument("--output", type=Path, default=None)
    args = p.parse_args()

    entrada = args.imagen.resolve()
    if not entrada.exists():
        print(f"No existe: {entrada}", file=sys.stderr)
        sys.exit(1)
    salida = args.output.resolve() if args.output else entrada.with_name(f"{entrada.stem}_con_texto.png")

    img = Image.open(entrada)
    out = render_text(img, args.texto, position=args.position, font_size=args.size)
    out.save(salida)
    print(f"✓ {salida}")


if __name__ == "__main__":
    main()
