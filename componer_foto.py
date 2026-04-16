#!/usr/bin/env python3
"""Componer una foto combinando un sujeto (PNG con alpha) sobre un fondo difuminado.

El fondo se redimensiona en modo "cover" (llena el canvas, cropea lo que sobra) y se
aplica un blur gaussiano. El sujeto se escala a un % del ancho de salida y se pega
centrado horizontalmente, con posición vertical configurable.

Uso:
    componer_foto <frente> <fondo> [opciones]

Ejemplos:
    componer_foto producto_sin_fondo.png paisaje.jpg
    componer_foto frente.png fondo.jpg --size 60 --position bottom --blur 25
    componer_foto frente.png fondo.jpg --width 1080 --height 1920 --output /tmp/out.png
"""
import argparse
import sys
from pathlib import Path

from PIL import Image, ImageFilter


def cover_resize(img: Image.Image, target: tuple[int, int]) -> Image.Image:
    """Redimensiona al modo 'cover': llena target, cropeando el exceso centrado."""
    tw, th = target
    sw, sh = img.size
    scale = max(tw / sw, th / sh)
    new_size = (max(tw, round(sw * scale)), max(th, round(sh * scale)))
    img = img.resize(new_size, Image.LANCZOS)
    nw, nh = img.size
    left = (nw - tw) // 2
    top = (nh - th) // 2
    return img.crop((left, top, left + tw, top + th))


def componer(
    frente_path: Path,
    fondo_path: Path,
    salida: Path,
    width: int = 1200,
    height: int = 1200,
    size_pct: float = 70.0,
    position: str = "center",
    blur: int = 15,
):
    fondo = Image.open(fondo_path).convert("RGB")
    fondo = cover_resize(fondo, (width, height))
    if blur > 0:
        fondo = fondo.filter(ImageFilter.GaussianBlur(radius=blur))
    canvas = fondo.convert("RGBA")

    frente = Image.open(frente_path).convert("RGBA")
    fw, fh = frente.size
    target_w = max(1, int(width * size_pct / 100))
    scale = target_w / fw
    target_h = max(1, round(fh * scale))
    frente = frente.resize((target_w, target_h), Image.LANCZOS)

    x = (width - target_w) // 2
    if position == "top":
        y = 0
    elif position == "bottom":
        y = height - target_h
    else:  # center
        y = (height - target_h) // 2

    canvas.alpha_composite(frente, dest=(x, y))
    canvas.convert("RGB").save(salida) if salida.suffix.lower() in {".jpg", ".jpeg"} else canvas.save(salida)
    print(f"Canvas: {width}×{height}  |  Sujeto: {target_w}×{target_h} ({size_pct}%)  |  Pos: {position}  |  Blur: {blur}px")
    print(f"✓ {salida}")


def main():
    p = argparse.ArgumentParser(
        description="Componer un sujeto (PNG con alpha) sobre un fondo difuminado.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("frente", type=Path, help="PNG con alpha (sujeto recortado)")
    p.add_argument("fondo", type=Path, help="Imagen de fondo (cualquier formato)")
    p.add_argument("--output", type=Path, default=None, help="Salida (default: <frente>_compuesta.png)")
    p.add_argument("--size", type=float, default=70.0, help="Tamaño del sujeto como %% del ancho (default 70)")
    p.add_argument("--position", choices=["top", "center", "bottom"], default="center")
    p.add_argument("--blur", type=int, default=15, help="Radio de blur gaussiano al fondo (default 15, 0 = sin blur)")
    p.add_argument("--width", type=int, default=1200, help="Ancho del canvas (default 1200)")
    p.add_argument("--height", type=int, default=1200, help="Alto del canvas (default 1200)")
    args = p.parse_args()

    frente = args.frente.resolve()
    fondo = args.fondo.resolve()
    for path in (frente, fondo):
        if not path.exists():
            print(f"No existe: {path}", file=sys.stderr)
            sys.exit(1)

    salida = args.output.resolve() if args.output else frente.with_name(f"{frente.stem}_compuesta.png")
    componer(frente, fondo, salida, args.width, args.height, args.size, args.position, args.blur)


if __name__ == "__main__":
    main()
