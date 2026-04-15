#!/usr/bin/env python3
"""Quitar fondo de una imagen usando BRIA RMBG 1.4 (local, gratis).

Uso:
    python3 quitar_fondo.py <entrada> [salida]

Si no se provee salida, usa <entrada>_sin_fondo.png en la misma carpeta.
"""
import sys
from pathlib import Path
import numpy as np
import torch
from PIL import Image
from torchvision.transforms.functional import normalize
from transformers import AutoModelForImageSegmentation

MODEL_ID = "briaai/RMBG-1.4"
INPUT_SIZE = (1024, 1024)


def preprocess(img: Image.Image) -> torch.Tensor:
    arr = np.array(img.convert("RGB"))
    t = torch.from_numpy(arr).permute(2, 0, 1).float().unsqueeze(0) / 255.0
    t = torch.nn.functional.interpolate(t, size=INPUT_SIZE, mode="bilinear")
    return normalize(t, [0.5, 0.5, 0.5], [1.0, 1.0, 1.0])


def postprocess(pred: torch.Tensor, orig_size) -> np.ndarray:
    pred = torch.nn.functional.interpolate(pred, size=orig_size[::-1], mode="bilinear")
    pred = pred.squeeze().cpu().numpy()
    pred = (pred - pred.min()) / (pred.max() - pred.min() + 1e-8)
    return (pred * 255).astype(np.uint8)


def quitar_fondo(entrada: Path, salida: Path):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = AutoModelForImageSegmentation.from_pretrained(MODEL_ID, trust_remote_code=True)
    model.to(device).eval()

    img = Image.open(entrada)
    x = preprocess(img).to(device)
    with torch.no_grad():
        pred = model(x)[0][0]
    mask = postprocess(pred, img.size)

    rgba = np.array(img.convert("RGBA"))
    rgba[:, :, 3] = mask
    Image.fromarray(rgba).save(salida)
    print(f"✓ {salida}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    entrada = Path(sys.argv[1]).resolve()
    salida = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else entrada.with_name(f"{entrada.stem}_sin_fondo.png")
    quitar_fondo(entrada, salida)


if __name__ == "__main__":
    main()
