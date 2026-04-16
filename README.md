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
chmod +x ~/bin/quitar_fondo ~/bin/mejorar_foto ~/bin/limpiar_fantasma

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
mejorar_foto foto.jpg                 # 1024x1024 → 4096x4096 → foto_mejorada.png
mejorar_foto foto.jpg salida.png      # path de salida custom
```

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

## Ejemplo de flujo combinado

Recortar fondo, limpiar residuos y mejorar resolución:
```bash
quitar_fondo producto.jpg
limpiar_fantasma producto_sin_fondo.png
mejorar_foto producto_sin_fondo_limpia.png
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
