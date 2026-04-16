#!/usr/bin/env python3
"""Limpiar regiones 'fantasma' de un PNG con alpha.

Elimina residuos del recorte: píxeles semitransparentes sueltos, islas pequeñas,
y zonas de baja saturación (gris residual del fondo original). Devuelve un PNG
con alpha binario más limpio en esas zonas, preservando los bordes suaves del
sujeto principal.

Uso:
    python3 limpiar_fantasma.py <entrada> [salida]

Si no se provee salida, usa <entrada>_limpia.png en la misma carpeta.

Heurísticas:
  1. Píxeles con alpha < MIN_ALPHA → alpha = 0 (ruido bajo).
  2. Islas conectadas más chicas que MIN_ISLAND_PX → borradas (fragmentos).
  3. Píxeles semitransparentes (alpha < SOLID_ALPHA) Y de baja saturación
     (HSV S < MIN_SAT) → borrados (neblina gris de fondo).
  4. Los bordes suaves del sujeto (alpha intermedio sobre píxeles coloridos
     adyacentes a zona sólida) se preservan.
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

MIN_ALPHA = 30           # debajo de esto es ruido, se borra
SOLID_ALPHA = 200        # arriba de esto es sujeto claro (preservar siempre)
MIN_ISLAND_PX = 500      # islas más chicas que esto se borran
MIN_SAT = 25             # saturación mínima (0-255) para no considerar "gris residual"
DILATE_SOLID = 3         # radio de dilatación del núcleo sólido para proteger bordes


def rgb_to_saturation(rgb: np.ndarray) -> np.ndarray:
    """Saturación HSV simplificada (0-255) a partir de RGB uint8."""
    r, g, b = rgb[..., 0].astype(np.int32), rgb[..., 1].astype(np.int32), rgb[..., 2].astype(np.int32)
    mx = np.maximum(np.maximum(r, g), b)
    mn = np.minimum(np.minimum(r, g), b)
    sat = np.where(mx == 0, 0, ((mx - mn) * 255 // np.maximum(mx, 1)))
    return sat.astype(np.uint8)


def limpiar(entrada: Path, salida: Path):
    img = Image.open(entrada).convert("RGBA")
    arr = np.array(img)
    rgb = arr[..., :3]
    alpha = arr[..., 3]

    pixels = alpha.size
    alpha_original_visible = (alpha > 0).sum()

    # --- 1. Ruido bajo: alpha < MIN_ALPHA ---
    clean = alpha.copy()
    clean[clean < MIN_ALPHA] = 0

    # --- 2. Islas pequeñas ---
    binary = clean > 0
    labels, n = ndimage.label(binary)
    if n > 0:
        sizes = ndimage.sum(binary, labels, range(1, n + 1)).astype(np.int64)
        remove_labels = np.where(sizes < MIN_ISLAND_PX)[0] + 1
        if len(remove_labels) > 0:
            mask_small = np.isin(labels, remove_labels)
            clean[mask_small] = 0
            binary = clean > 0

    # --- 3. Neblina gris: semitransparente + baja saturación, lejos del núcleo sólido ---
    solid = clean >= SOLID_ALPHA
    solid_dilated = ndimage.binary_dilation(solid, iterations=DILATE_SOLID)
    sat = rgb_to_saturation(rgb)
    haze = (clean > 0) & (clean < SOLID_ALPHA) & (sat < MIN_SAT) & (~solid_dilated)
    clean[haze] = 0

    out = arr.copy()
    out[..., 3] = clean

    eliminated = alpha_original_visible - (clean > 0).sum()
    print(f"Píxeles visibles originales: {alpha_original_visible:,} / {pixels:,}")
    print(f"Píxeles fantasma eliminados: {eliminated:,}")
    print(f"  • ruido bajo (alpha<{MIN_ALPHA}): {((alpha > 0) & (alpha < MIN_ALPHA)).sum():,}")
    print(f"  • islas <{MIN_ISLAND_PX}px: {int(sizes[sizes < MIN_ISLAND_PX].sum()) if n > 0 else 0:,}")
    print(f"  • neblina gris: {haze.sum():,}")

    Image.fromarray(out).save(salida)
    print(f"✓ {salida}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    entrada = Path(sys.argv[1]).resolve()
    salida = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else entrada.with_name(f"{entrada.stem}_limpia.png")
    limpiar(entrada, salida)


if __name__ == "__main__":
    main()
