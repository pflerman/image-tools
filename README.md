# image-tools

Scripts Python locales para procesar imágenes sin depender de APIs pagas ni servicios online. Todo corre offline, gratis, sin límites de uso.

## Scripts

### `quitar_fondo.py` — Remover fondo con transparencia real

Usa **BRIA RMBG 1.4** (modelo de segmentación state-of-the-art) vía `transformers`. Devuelve PNG con canal alpha real. Mejor calidad que `rembg` (U2Net) especialmente en bordes finos, pelo, objetos translúcidos.

**Uso:**
```bash
python3 quitar_fondo.py foto.jpg                 # → foto_sin_fondo.png
python3 quitar_fondo.py foto.jpg salida.png      # path de salida custom
```

**Dependencias:** `transformers<4.50`, `torch`, `torchvision`, `pillow`, `numpy`.
**Modelo:** ~180MB, cacheado en `~/.cache/huggingface/` la primera vez.
**Performance CPU:** ~5-10s por foto.

---

### `mejorar_foto.py` — Upscale x4 con Real-ESRGAN

Mejora resolución y calidad de fotos de baja calidad usando **Real-ESRGAN x4plus** vía `spandrel` (el reemplazo moderno de `basicsr`, compatible con Python 3.14).

**Uso:**
```bash
python3 mejorar_foto.py foto.jpg                 # 1024x1024 → 4096x4096 _mejorada.png
python3 mejorar_foto.py foto.jpg salida.png      # path de salida custom
```

**Dependencias:** `spandrel`, `torch`, `pillow`, `numpy`.
**Modelo:** `RealESRGAN_x4plus.pth` (~65MB), cacheado en `~/.cache/spandrel/` la primera vez.
**Performance CPU:** ~30-60s para 1024×1024. Procesa en tiles de 256px para no agotar RAM.

---

## Instalación

```bash
pip install --user "transformers<4.50" torch torchvision pillow numpy spandrel
```

En Python 3.14 hay que pinear `transformers<4.50` porque versiones nuevas rompen el `trust_remote_code` de BRIA.

## Por qué estos modelos

| Tarea | Elección | Alternativa descartada | Motivo |
|---|---|---|---|
| Quitar fondo | BRIA RMBG 1.4 | rembg (U2Net) | BRIA más nítido en bordes |
| Quitar fondo | BRIA RMBG 1.4 | Gemini edit_image | Gemini no genera alpha real, hornea el patrón ajedrezado |
| Upscale | Real-ESRGAN via spandrel | realesrgan+basicsr | basicsr rota en Python 3.14 (APIs de torchvision removidas) |

## Ejemplos de flujo combinado

Recortar y luego mejorar resolución:
```bash
python3 quitar_fondo.py producto.jpg
python3 mejorar_foto.py producto_sin_fondo.png
```
