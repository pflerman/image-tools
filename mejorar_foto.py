#!/usr/bin/env python3
"""Redimensionar una foto con PIL (LANCZOS).

Uso:
    python3 mejorar_foto.py <entrada> [salida] [--width N] [--height N]

Si no se provee salida, usa <entrada>_mejorada.png en la misma carpeta.

Tamaño:
    - sin --width ni --height: clamp a MAX_OUTPUT_SIZE (1200px) manteniendo aspect ratio
    - solo --width o solo --height: resize manteniendo aspect ratio
    - ambos: resize al tamaño exacto (sin mantener proporción)
"""
import argparse
import sys
from pathlib import Path

from PIL import Image

MAX_OUTPUT_SIZE = 1200


def _target_size(current: tuple[int, int], width: int | None, height: int | None) -> tuple[int, int] | None:
    """Calcula el tamaño de salida deseado según --width/--height.

    - ambos: tamaño exacto (sin mantener proporción)
    - uno solo: calcula el otro manteniendo aspect ratio
    - ninguno: None (se aplica clamp por MAX_OUTPUT_SIZE)
    """
    cw, ch = current
    if width and height:
        return (width, height)
    if width:
        return (width, round(ch * width / cw))
    if height:
        return (round(cw * height / ch), height)
    return None


def mejorar(entrada: Path, salida: Path, width: int | None = None, height: int | None = None):
    img = Image.open(entrada)
    print(f"Entrada: {img.size}")

    target = _target_size(img.size, width, height)
    if target:
        print(f"Redimensionando {img.size} → {target}")
        img = img.resize(target, Image.LANCZOS)
    elif max(img.size) > MAX_OUTPUT_SIZE:
        print(f"Redimensionando {img.size} → max {MAX_OUTPUT_SIZE}px (aspect ratio preservado)")
        img.thumbnail((MAX_OUTPUT_SIZE, MAX_OUTPUT_SIZE), Image.LANCZOS)

    img.save(salida)
    print(f"✓ {salida} ({img.size})")


def main():
    p = argparse.ArgumentParser(
        description="Redimensionar con PIL LANCZOS. Output clampado a 1200px salvo que se pase --width/--height.",
    )
    p.add_argument("entrada", type=Path)
    p.add_argument("salida", type=Path, nargs="?", default=None)
    p.add_argument("--width", type=int, default=None, help="Ancho exacto de salida en px")
    p.add_argument("--height", type=int, default=None, help="Alto exacto de salida en px")
    args = p.parse_args()

    entrada = args.entrada.resolve()
    salida = args.salida.resolve() if args.salida else entrada.with_name(f"{entrada.stem}_mejorada.png")
    mejorar(entrada, salida, args.width, args.height)


if __name__ == "__main__":
    main()
