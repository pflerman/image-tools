#!/usr/bin/env python3
"""Cropear el espacio transparente sobrante de un PNG con alpha.

Detecta el bounding box de los píxeles opacos y recorta la imagen a ese rectángulo,
con un padding opcional en píxeles (clampeado a los bordes).

Uso:
    python3 cropear.py <entrada> [padding_px] [salida]

Ejemplos:
    python3 cropear.py foto.png              # → foto_cropeada.png, padding 0
    python3 cropear.py foto.png 20           # → foto_cropeada.png, padding 20px
    python3 cropear.py foto.png 20 out.png   # salida custom, padding 20px
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image


def cropear(entrada: Path, salida: Path, padding: int = 0):
    img = Image.open(entrada).convert("RGBA")
    alpha = np.array(img)[..., 3]
    ys, xs = np.where(alpha > 0)
    if len(xs) == 0:
        print("⚠ Imagen completamente transparente, no se cropea")
        img.save(salida)
        return

    h, w = alpha.shape
    left = max(0, xs.min() - padding)
    right = min(w, xs.max() + 1 + padding)
    top = max(0, ys.min() - padding)
    bottom = min(h, ys.max() + 1 + padding)

    cropped = img.crop((left, top, right, bottom))
    cropped.save(salida)
    print(f"Original: {w}×{h}  →  Cropeada: {cropped.size[0]}×{cropped.size[1]}  (padding {padding}px)")
    print(f"✓ {salida}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    entrada = Path(sys.argv[1]).resolve()
    padding = 0
    salida = None

    if len(sys.argv) >= 3:
        try:
            padding = int(sys.argv[2])
            if len(sys.argv) >= 4:
                salida = Path(sys.argv[3]).resolve()
        except ValueError:
            salida = Path(sys.argv[2]).resolve()

    if salida is None:
        salida = entrada.with_name(f"{entrada.stem}_cropeada.png")

    cropear(entrada, salida, padding)


if __name__ == "__main__":
    main()
