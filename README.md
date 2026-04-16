# image-tools

Scripts Python locales para procesar imágenes sin depender de APIs pagas ni servicios online. Todo corre offline, gratis, sin límites de uso.

Corre en un **venv dedicado con Python 3.12** para aislarse de cambios del sistema y tener versiones pineadas.

## Instalación

```bash
git clone https://github.com/pflerman/image-tools ~/Proyectos/image-tools
cd ~/Proyectos/image-tools
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

### Wrappers en `~/bin/` (recomendado)

Los scripts se invocan como comandos globales (`quitar_fondo foto.jpg`) gracias a los wrappers en `~/bin/` que activan automáticamente el venv:

```bash
mkdir -p ~/bin
cat > ~/bin/quitar_fondo <<'EOF'
#!/bin/bash
exec ~/Proyectos/image-tools/.venv/bin/python ~/Proyectos/image-tools/quitar_fondo.py "$@"
EOF
cat > ~/bin/mejorar_foto <<'EOF'
#!/bin/bash
exec ~/Proyectos/image-tools/.venv/bin/python ~/Proyectos/image-tools/mejorar_foto.py "$@"
EOF
cat > ~/bin/limpiar_fantasma <<'EOF'
#!/bin/bash
exec ~/Proyectos/image-tools/.venv/bin/python ~/Proyectos/image-tools/limpiar_fantasma.py "$@"
EOF
cat > ~/bin/cropear <<'EOF'
#!/bin/bash
exec ~/Proyectos/image-tools/.venv/bin/python ~/Proyectos/image-tools/cropear.py "$@"
EOF
cat > ~/bin/agregar_texto <<'EOF'
#!/bin/bash
exec ~/Proyectos/image-tools/.venv/bin/python ~/Proyectos/image-tools/agregar_texto.py "$@"
EOF
cat > ~/bin/procesar_foto <<'EOF'
#!/bin/bash
exec ~/Proyectos/image-tools/.venv/bin/python ~/Proyectos/image-tools/procesar_foto.py "$@"
EOF
chmod +x ~/bin/quitar_fondo ~/bin/mejorar_foto ~/bin/limpiar_fantasma ~/bin/cropear ~/bin/agregar_texto ~/bin/procesar_foto

# Agregar ~/bin al PATH si no está
grep -q 'HOME/bin' ~/.bashrc || echo 'export PATH="$HOME/bin:$PATH"' >> ~/.bashrc
```

## Scripts

### `quitar_fondo` — Remover fondo con transparencia real

Usa **BRIA RMBG 1.4** (modelo de segmentación state-of-the-art) vía `transformers`. Devuelve PNG con canal alpha real. Mejor calidad que `rembg` (U2Net) especialmente en bordes finos, pelo, objetos translúcidos.

**Uso:**
```bash
quitar_fondo foto.jpg                 # → foto_sin_fondo.png (misma carpeta)
quitar_fondo foto.jpg salida.png      # path de salida custom
```

**Modelo:** ~180MB, cacheado en `~/.cache/huggingface/` la primera vez.
**Performance CPU:** ~5-10s por foto.

---

### `mejorar_foto` — Upscale x4 con Real-ESRGAN

Mejora resolución y calidad de fotos de baja calidad usando **Real-ESRGAN x4plus** vía `spandrel` (el reemplazo moderno de `basicsr`, sin los problemas de compat).

**Uso:**
```bash
mejorar_foto foto.jpg                         # upscale x4, clampado a 1200px max
mejorar_foto foto.jpg salida.png              # path de salida custom
mejorar_foto foto.jpg --width 800             # 800px de ancho, alto proporcional
mejorar_foto foto.jpg --height 600            # 600px de alto, ancho proporcional
mejorar_foto foto.jpg --width 1024 --height 1024  # tamaño exacto (no mantiene proporción)
```

**Opciones:**
- `--width N` — ancho de salida en px
- `--height N` — alto de salida en px
- Sin flags: clampa a `MAX_OUTPUT_SIZE` (1200px lado mayor) manteniendo aspect ratio
- Solo uno: calcula el otro manteniendo aspect ratio
- Ambos: tamaño exacto sin mantener proporción

**Modelo:** `RealESRGAN_x4plus.pth` (~65MB), cacheado en `~/.cache/spandrel/` la primera vez.
**Performance CPU:** ~30-60s para 1024×1024. Procesa en tiles de 256px para no agotar RAM.

---

### `limpiar_fantasma` — Eliminar residuos de un recorte con alpha

Limpia regiones "fantasma" de un PNG con canal alpha: píxeles semitransparentes sueltos, islas pequeñas desconectadas del sujeto, y neblina gris de baja saturación que dejó el modelo de segmentación. Preserva los bordes suaves legítimos (pelo, cristal) adyacentes a zonas sólidas.

**Uso:**
```bash
limpiar_fantasma foto_sin_fondo.png                    # → foto_sin_fondo_limpia.png
limpiar_fantasma foto_sin_fondo.png salida.png         # path de salida custom
```

**Heurísticas** (tuneables en el script):
- `alpha < 30` → ruido, eliminado
- Islas conectadas < 500 píxeles → fragmentos, eliminados
- Semitransparente + saturación < 25 + lejos del núcleo sólido → neblina gris, eliminada

Imprime un reporte de cuántos píxeles limpió por categoría.

---

### `cropear` — Recortar el espacio transparente sobrante

Detecta el bounding box de los píxeles opacos y cropea la imagen a ese rectángulo, con padding opcional en píxeles.

**Uso:**
```bash
cropear foto.png                  # → foto_cropeada.png, sin padding
cropear foto.png 20               # con 20px de padding
cropear foto.png 20 salida.png    # con padding + salida custom
```

### `agregar_texto` — Overlay de texto con contraste y posición automática

Agrega texto a una imagen eligiendo color de texto (blanco o negro + contorno opuesto) según la luminancia del área donde cae, y ubicándolo en la banda (top/bottom) con menos "busyness" para no pisar al sujeto. Wrap automático si el texto es largo.

**Uso:**
```bash
agregar_texto foto.png 'Mi título'
agregar_texto foto.png 'Oferta' --position top --size 80
agregar_texto foto.png 'Texto largo que wrappea' --output out.png
```

**Opciones:**
- `--position {top,bottom,auto}` — default `auto` (elige la banda con menor varianza/más alpha)
- `--size N` — tamaño de fuente en px (default `ancho/18`)
- `--output PATH` — default `<entrada>_con_texto.png`

Usa DejaVu Sans Bold (fallback a Liberation/Noto/default). Imprime el color dominante y la decisión de posición.

---

### `procesar_foto` — Pipeline completo en un comando

Ejecuta en orden: `quitar_fondo` → `limpiar_fantasma` → `cropear` → `agregar_texto` (opcional) → `mejorar_foto`. Usa archivos intermedios en un tempdir, así solo queda el resultado final.

**Uso:**
```bash
procesar_foto foto.jpg                              # sin texto (4 pasos)
procesar_foto foto.jpg 'Oferta especial'            # con texto (5 pasos)
procesar_foto foto.jpg 'Oferta' --position top --size 80 --padding 30
procesar_foto foto.jpg --output /tmp/out.png
```

**Opciones:**
- `--padding N` — padding del crop en px (default `20`)
- `--position {top,bottom,auto}` — default `auto`
- `--size N` — tamaño de fuente en px
- `--width N` / `--height N` — pasan directo a `mejorar_foto` (ver reglas ahí). Sin flags: max 1200px.
- `--output PATH` — default `<entrada>_procesada.png`

```bash
procesar_foto foto.jpg 'Oferta'                            # → max 1200px (default)
procesar_foto foto.jpg 'Oferta' --width 800                # → 800px ancho, alto proporcional
procesar_foto foto.jpg 'Oferta' --height 600               # → 600px alto, ancho proporcional
procesar_foto foto.jpg 'Oferta' --width 800 --height 600   # → exacto, sin proporción
```

Imprime el progreso de cada paso y el tiempo total.

---

## Flujo manual paso a paso

Si preferís controlar cada etapa (o inspeccionar intermediarios):
```bash
quitar_fondo producto.jpg
limpiar_fantasma producto_sin_fondo.png
cropear producto_sin_fondo_limpia.png 20
agregar_texto producto_sin_fondo_limpia_cropeada.png 'Texto'
mejorar_foto producto_sin_fondo_limpia_cropeada_con_texto.png
```

## Por qué estos modelos

| Tarea | Elección | Alternativa descartada | Motivo |
|---|---|---|---|
| Quitar fondo | BRIA RMBG 1.4 | rembg (U2Net) | BRIA más nítido en bordes |
| Quitar fondo | BRIA RMBG 1.4 | Gemini edit_image | Gemini no genera alpha real, hornea el patrón ajedrezado |
| Upscale | Real-ESRGAN via spandrel | realesrgan+basicsr | basicsr rota en Python 3.14+ (APIs de torchvision removidas) |

## Por qué venv con Python 3.12

- **Aislado del sistema**: `dnf update` no puede romper las deps.
- **Python 3.12** tiene soporte estable de torch/torchvision. 3.14 tiene wheels pero sigue siendo terreno reciente.
- **requirements.txt pineado**: cualquier breaking de transformers/torch/spandrel no te afecta hasta que decidas actualizar.

Para actualizar versiones a propósito:
```bash
cd ~/Proyectos/image-tools
.venv/bin/pip install -U transformers torch torchvision spandrel pillow numpy
.venv/bin/pip freeze > requirements.txt
# probar que ande, commitear
```
