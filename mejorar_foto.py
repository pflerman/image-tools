#!/usr/bin/env python3
"""Mejorar resolución y calidad de una foto usando Real-ESRGAN x4 via spandrel.

Uso:
    python3 mejorar_foto.py <entrada> [salida]

Si no se provee salida, usa <entrada>_mejorada.png en la misma carpeta.
La primera ejecución descarga el modelo (~65MB) y queda cacheado.
"""
import sys
import urllib.request
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from spandrel import ModelLoader

MODEL_URL = "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth"
MODEL_PATH = Path.home() / ".cache" / "spandrel" / "RealESRGAN_x4plus.pth"
TILE_SIZE = 256  # procesar en tiles para no agotar RAM
TILE_PAD = 16
MAX_OUTPUT_SIZE = 1200


def download_model():
    if MODEL_PATH.exists():
        return
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    print(f"Descargando modelo a {MODEL_PATH}...")
    urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
    print("✓ modelo descargado")


def upscale_tiled(model, img_tensor, scale, device):
    _, _, h, w = img_tensor.shape
    out = torch.zeros((1, 3, h * scale, w * scale), device=device)
    for y in range(0, h, TILE_SIZE):
        for x in range(0, w, TILE_SIZE):
            y0, x0 = max(0, y - TILE_PAD), max(0, x - TILE_PAD)
            y1, x1 = min(h, y + TILE_SIZE + TILE_PAD), min(w, x + TILE_SIZE + TILE_PAD)
            tile = img_tensor[:, :, y0:y1, x0:x1]
            with torch.no_grad():
                up = model(tile)
            # recortar el padding
            top = (y - y0) * scale
            left = (x - x0) * scale
            th = min(TILE_SIZE, h - y) * scale
            tw = min(TILE_SIZE, w - x) * scale
            out[:, :, y * scale:y * scale + th, x * scale:x * scale + tw] = \
                up[:, :, top:top + th, left:left + tw]
    return out


def mejorar(entrada: Path, salida: Path):
    download_model()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Cargando modelo en {device}...")
    model = ModelLoader().load_from_file(MODEL_PATH).eval().to(device)
    scale = model.scale

    img = Image.open(entrada).convert("RGB")
    print(f"Entrada: {img.size} → salida x{scale}: {(img.size[0]*scale, img.size[1]*scale)}")

    arr = np.array(img).astype(np.float32) / 255.0
    t = torch.from_numpy(arr).permute(2, 0, 1).unsqueeze(0).to(device)
    up = upscale_tiled(model.model, t, scale, device)
    up = up.clamp(0, 1).squeeze(0).permute(1, 2, 0).cpu().numpy()
    out_img = Image.fromarray((up * 255).astype(np.uint8))
    if max(out_img.size) > MAX_OUTPUT_SIZE:
        print(f"Redimensionando {out_img.size} → max {MAX_OUTPUT_SIZE}px (aspect ratio preservado)")
        out_img.thumbnail((MAX_OUTPUT_SIZE, MAX_OUTPUT_SIZE), Image.LANCZOS)
    out_img.save(salida)
    print(f"✓ {salida} ({out_img.size})")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    entrada = Path(sys.argv[1]).resolve()
    salida = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else entrada.with_name(f"{entrada.stem}_mejorada.png")
    mejorar(entrada, salida)


if __name__ == "__main__":
    main()
