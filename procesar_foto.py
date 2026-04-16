#!/usr/bin/env python3
"""Pipeline completo: quitar_fondo → limpiar_fantasma → cropear → agregar_texto → mejorar_foto.

Uso:
    procesar_foto <imagen> [texto] [opciones]

Ejemplos:
    procesar_foto foto.jpg
    procesar_foto foto.jpg 'Oferta especial'
    procesar_foto foto.jpg 'Oferta' --padding 30 --position top --size 80
    procesar_foto foto.jpg --output /tmp/out.png

Si no se pasa texto, se saltea el paso de agregar_texto.
El resultado queda en <entrada>_procesada.png (o en --output).
"""
import argparse
import sys
import tempfile
import time
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
import quitar_fondo
import limpiar_fantasma
import cropear
import agregar_texto
import mejorar_foto


def step(n: int, total: int, name: str):
    print(f"\n[{n}/{total}] {name}")
    print("─" * 50)


def procesar(entrada: Path, salida: Path, texto: str | None, padding: int,
             position: str, font_size: int | None,
             width: int | None = None, height: int | None = None):
    total = 5 if texto else 4
    n = 0
    t0 = time.time()

    with tempfile.TemporaryDirectory(prefix="procesar_foto_") as tmpdir:
        tmp = Path(tmpdir)

        n += 1; step(n, total, "Quitar fondo (BRIA RMBG 1.4)")
        p1 = tmp / "1_sin_fondo.png"
        quitar_fondo.quitar_fondo(entrada, p1)

        n += 1; step(n, total, "Limpiar fantasma")
        p2 = tmp / "2_limpia.png"
        limpiar_fantasma.limpiar(p1, p2)

        n += 1; step(n, total, f"Cropear (padding {padding}px)")
        p3 = tmp / "3_cropeada.png"
        cropear.cropear(p2, p3, padding)

        current = p3

        if texto:
            n += 1; step(n, total, f"Agregar texto: {texto!r}")
            p4 = tmp / "4_con_texto.png"
            img = Image.open(current)
            out_img = agregar_texto.render_text(img, texto, position=position, font_size=font_size)
            out_img.save(p4)
            print(f"✓ {p4}")
            current = p4

        n += 1; step(n, total, "Mejorar resolución x4 (Real-ESRGAN)")
        mejorar_foto.mejorar(current, salida, width=width, height=height)

    dt = time.time() - t0
    print(f"\n{'═' * 50}")
    print(f"✓ Procesado en {dt:.1f}s → {salida}")


def main():
    p = argparse.ArgumentParser(
        description="Pipeline completo de procesamiento de foto.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("imagen", type=Path)
    p.add_argument("texto", nargs="?", default=None, help="Texto opcional para overlay")
    p.add_argument("--padding", type=int, default=20, help="Padding del crop en px (default 20)")
    p.add_argument("--position", choices=["top", "bottom", "auto"], default="auto")
    p.add_argument("--size", type=int, default=None, help="Tamaño de fuente en px")
    p.add_argument("--output", type=Path, default=None)
    p.add_argument("--width", type=int, default=None, help="Ancho de salida en px (pasa a mejorar_foto)")
    p.add_argument("--height", type=int, default=None, help="Alto de salida en px (pasa a mejorar_foto)")
    args = p.parse_args()

    entrada = args.imagen.resolve()
    if not entrada.exists():
        print(f"No existe: {entrada}", file=sys.stderr)
        sys.exit(1)
    salida = args.output.resolve() if args.output else entrada.with_name(f"{entrada.stem}_procesada.png")

    procesar(entrada, salida, args.texto, args.padding, args.position, args.size,
             width=args.width, height=args.height)


if __name__ == "__main__":
    main()
