#!/usr/bin/env python3
"""Herramienta visual interactiva para agregar cotas de medidas a imágenes de producto.

Se abre la imagen en una ventana Tkinter. Click izquierdo en punto A, click en
punto B, se pide la medida y se dibuja la cota. Click derecho para callouts de
texto libre con un solo click (ej: "Bisagras reforzadas"). Ambos conviven.

Uso:
    python3 acotar_interactivo.py <imagen> [--unidad cm] [--fondo blanco|transparente] [--margen N] [--escala F]

Ejemplos:
    python3 acotar_interactivo.py producto.png
    python3 acotar_interactivo.py producto.png --unidad mm
    python3 acotar_interactivo.py producto.png --fondo transparente --margen 150
    python3 acotar_interactivo.py producto.png --escala 2
"""
import argparse
import math
import sys
import tkinter as tk
from pathlib import Path

from PIL import Image, ImageDraw, ImageTk

sys.path.insert(0, str(Path(__file__).parent))
from acotar_foto import (
    LINE_COLOR, LINE_WIDTH, ARROW_SIZE, EXT_OVERSHOOT,
    LABEL_BG, LABEL_PAD_X, LABEL_PAD_Y, LABEL_BORDER,
    find_font, format_measure,
)

MAX_DISPLAY = 800
DEFAULT_MARGEN = 100
LINE_COLOR_HEX = "#{:02x}{:02x}{:02x}".format(*LINE_COLOR)
BG_BLANCO = (255, 255, 255, 255)
BG_TRANSPARENTE = (0, 0, 0, 0)


def _arrow_angled(draw: ImageDraw.Draw, tx: float, ty: float,
                  ux: float, uy: float, arrow_size: float):
    """Flecha con punta en (tx,ty) apuntando en dirección (ux,uy)."""
    bx = tx - ux * arrow_size
    by = ty - uy * arrow_size
    px, py = -uy, ux
    hw = arrow_size / 2
    pts = [
        (round(tx), round(ty)),
        (round(bx + px * hw), round(by + py * hw)),
        (round(bx - px * hw), round(by - py * hw)),
    ]
    draw.polygon(pts, fill=LINE_COLOR)


def _rotated_label(img: Image.Image, cx: float, cy: float, text: str,
                   font, angle_rad: float, escala: float):
    """Label con fondo, rotado paralelo a la línea de cota."""
    pad_x = round(LABEL_PAD_X * escala)
    pad_y = round(LABEL_PAD_Y * escala)
    probe = ImageDraw.Draw(img)
    bbox = probe.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    lw = tw + pad_x * 2
    lh = th + pad_y * 2

    tmp = Image.new("RGBA", (lw, lh), (0, 0, 0, 0))
    d = ImageDraw.Draw(tmp)
    d.rounded_rectangle((0, 0, lw - 1, lh - 1), radius=max(2, round(4 * escala)),
                        fill=LABEL_BG, outline=LABEL_BORDER, width=1)
    d.text((pad_x - bbox[0], pad_y - bbox[1]), text,
           fill=LINE_COLOR, font=font)

    rot_deg = -math.degrees(angle_rad)
    if rot_deg > 90:
        rot_deg -= 180
    elif rot_deg < -90:
        rot_deg += 180

    rotated = tmp.rotate(rot_deg, expand=True, resample=Image.BICUBIC)
    px = int(round(cx - rotated.width / 2))
    py = int(round(cy - rotated.height / 2))
    px = max(0, min(px, img.width - rotated.width))
    py = max(0, min(py, img.height - rotated.height))
    img.alpha_composite(rotated, (px, py))


def draw_cota(img: Image.Image, ax: int, ay: int, bx: int, by: int,
              label: str, font, escala: float = 1.0):
    """Dibuja una cota completa entre dos puntos en cualquier ángulo."""
    dx = bx - ax
    dy = by - ay
    length = math.hypot(dx, dy)
    if length < 2:
        return
    ux, uy = dx / length, dy / length
    px, py = -uy, ux

    line_w = max(1, round(LINE_WIDTH * escala))
    arrow_s = ARROW_SIZE * escala
    ext_s = EXT_OVERSHOOT * escala

    draw = ImageDraw.Draw(img)

    draw.line([(ax, ay), (bx, by)], fill=LINE_COLOR, width=line_w)

    for x, y in [(ax, ay), (bx, by)]:
        draw.line([
            (round(x - px * ext_s), round(y - py * ext_s)),
            (round(x + px * ext_s), round(y + py * ext_s)),
        ], fill=LINE_COLOR, width=line_w)

    _arrow_angled(draw, ax, ay, ux, uy, arrow_s)
    _arrow_angled(draw, bx, by, -ux, -uy, arrow_s)

    mid_x = (ax + bx) / 2
    mid_y = (ay + by) / 2
    angle_rad = math.atan2(dy, dx)
    _rotated_label(img, mid_x, mid_y, label, font, angle_rad, escala)


CALLOUT_LENGTH = 80


def _horizontal_label(img: Image.Image, cx: float, cy: float, text: str,
                      font, escala: float):
    """Label horizontal con fondo, centrado en (cx, cy)."""
    pad_x = round(LABEL_PAD_X * escala)
    pad_y = round(LABEL_PAD_Y * escala)
    probe = ImageDraw.Draw(img)
    bbox = probe.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    lw = tw + pad_x * 2
    lh = th + pad_y * 2

    tmp = Image.new("RGBA", (lw, lh), (0, 0, 0, 0))
    d = ImageDraw.Draw(tmp)
    d.rounded_rectangle((0, 0, lw - 1, lh - 1), radius=max(2, round(4 * escala)),
                        fill=LABEL_BG, outline=LABEL_BORDER, width=1)
    d.text((pad_x - bbox[0], pad_y - bbox[1]), text,
           fill=LINE_COLOR, font=font)

    px = int(round(cx - lw / 2))
    py = int(round(cy - lh / 2))
    px = max(0, min(px, img.width - lw))
    py = max(0, min(py, img.height - lh))
    img.alpha_composite(tmp, (px, py))


def draw_callout(img: Image.Image, px: int, py: int, text: str, font,
                 img_w: int, img_h: int, escala: float = 1.0):
    """Dibuja un callout: flecha en el punto, línea diagonal hacia afuera, label horizontal."""
    cx, cy = img_w / 2, img_h / 2
    dx = px - cx
    dy = py - cy
    dist = math.hypot(dx, dy)
    if dist < 1:
        dx, dy, dist = 1.0, -1.0, math.sqrt(2)
    ux, uy = dx / dist, dy / dist

    length = CALLOUT_LENGTH * escala
    ex = px + ux * length
    ey = py + uy * length

    line_w = max(1, round(LINE_WIDTH * escala))
    arrow_s = ARROW_SIZE * escala

    draw = ImageDraw.Draw(img)
    draw.line([(px, py), (round(ex), round(ey))], fill=LINE_COLOR, width=line_w)
    _arrow_angled(draw, px, py, -ux, -uy, arrow_s)

    _horizontal_label(img, ex, ey, text, font, escala)


class AcotarApp:
    def __init__(self, root: tk.Tk, img_path: Path, unidad: str,
                 fondo: str = "blanco", margen: int = DEFAULT_MARGEN,
                 escala: float = 1.0):
        self.root = root
        self.img_path = img_path
        self.unidad = unidad
        self.fondo = fondo
        self.escala = escala

        src = Image.open(img_path).convert("RGBA")
        bg_color = BG_BLANCO if fondo == "blanco" else BG_TRANSPARENTE
        canvas_w = src.width + margen * 2
        canvas_h = src.height + margen * 2
        base = Image.new("RGBA", (canvas_w, canvas_h), bg_color)
        if fondo == "blanco":
            flat = Image.new("RGBA", src.size, BG_BLANCO)
            flat.alpha_composite(src)
            base.paste(flat, (margen, margen))
        else:
            base.alpha_composite(src, (margen, margen))
        self.original = base
        self.orig_w, self.orig_h = self.original.size

        self.items: list[tuple] = []
        self.point_a: tuple[int, int] | None = None
        self.preview_ids: list[int] = []

        font_size = max(14, round(min(self.orig_w, self.orig_h) / 22 * escala))
        self.font = find_font(font_size)

        self.root.title(f"Acotar — {img_path.name}")

        try:
            self.root.attributes("-zoomed", True)
        except tk.TclError:
            self.root.state("zoomed")

        screen_w = self.root.winfo_screenwidth() - 40
        screen_h = self.root.winfo_screenheight() - 120

        self.scale = min(screen_w / self.orig_w, screen_h / self.orig_h, 1.0)
        self.disp_w = round(self.orig_w * self.scale)
        self.disp_h = round(self.orig_h * self.scale)

        self.canvas = tk.Canvas(root, width=self.disp_w, height=self.disp_h,
                                cursor="crosshair")
        self.canvas.pack(side=tk.TOP, expand=True)

        btn_frame = tk.Frame(root)
        btn_frame.pack(side=tk.TOP, fill=tk.X, padx=8, pady=4)
        tk.Button(btn_frame, text="Deshacer", command=self.undo).pack(side=tk.LEFT, padx=4)
        tk.Button(btn_frame, text="Guardar", command=self.save).pack(side=tk.LEFT, padx=4)
        self.status = tk.Label(root, text="", anchor=tk.W, padx=8)
        self.status.pack(side=tk.BOTTOM, fill=tk.X)

        self.canvas.bind("<Button-1>", self._on_click_left)
        self.canvas.bind("<Button-3>", self._on_click_right)
        self.canvas.bind("<Motion>", self.on_motion)
        self.root.bind("<Escape>", self.on_escape)

        self._update_status_idle()
        self.redraw()

    def _update_status_idle(self):
        n = len(self.items)
        self.status.config(
            text=f"Izq: cota de medida | Der: callout de texto  "
                 f"({n} elemento{'s' if n != 1 else ''})"
        )

    def _to_orig(self, dx: int, dy: int) -> tuple[int, int]:
        return round(dx / self.scale), round(dy / self.scale)

    def _to_disp(self, ox: int, oy: int) -> tuple[int, int]:
        return round(ox * self.scale), round(oy * self.scale)

    def _clear_preview(self):
        for item_id in self.preview_ids:
            self.canvas.delete(item_id)
        self.preview_ids.clear()

    def _on_click_left(self, event):
        ox, oy = self._to_orig(event.x, event.y)
        ox = max(0, min(ox, self.orig_w - 1))
        oy = max(0, min(oy, self.orig_h - 1))

        if self.point_a is None:
            self.point_a = (ox, oy)
            r = 5
            item = self.canvas.create_oval(
                event.x - r, event.y - r, event.x + r, event.y + r,
                fill=LINE_COLOR_HEX, outline="white", width=2,
            )
            self.preview_ids.append(item)
            self.status.config(text="Click izq en el punto B de la cota  (Esc para cancelar)")
        else:
            bx, by = ox, oy
            ax, ay = self.point_a
            self._clear_preview()
            self.point_a = None
            measure = self._ask_measure()
            if measure is not None:
                label = f"{format_measure(measure)} {self.unidad}"
                self.items.append(("cota", ax, ay, bx, by, label))
                self.redraw()
            self._update_status_idle()

    def _on_click_right(self, event):
        if self.point_a is not None:
            return
        ox, oy = self._to_orig(event.x, event.y)
        ox = max(0, min(ox, self.orig_w - 1))
        oy = max(0, min(oy, self.orig_h - 1))
        text = self._ask_text()
        if text:
            self.items.append(("callout", ox, oy, text))
            self.redraw()
            self._update_status_idle()

    def on_motion(self, event):
        if self.point_a is None:
            return
        while len(self.preview_ids) > 1:
            self.canvas.delete(self.preview_ids.pop())
        ax_d, ay_d = self._to_disp(*self.point_a)
        item = self.canvas.create_line(
            ax_d, ay_d, event.x, event.y,
            fill=LINE_COLOR_HEX, dash=(6, 4), width=2,
        )
        self.preview_ids.append(item)

    def on_escape(self, event=None):
        if self.point_a is not None:
            self.point_a = None
            self._clear_preview()
            self._update_status_idle()

    def _ask_measure(self) -> float | None:
        dlg = tk.Toplevel(self.root)
        dlg.title("Medida")
        dlg.resizable(False, False)

        tk.Label(dlg, text=f"Medida ({self.unidad}):").pack(padx=16, pady=(16, 4))
        entry = tk.Entry(dlg, width=15, justify=tk.CENTER, font=("sans-serif", 14))
        entry.pack(padx=16, pady=4)

        result: list[float | None] = [None]

        def confirm(event=None):
            text = entry.get().strip().replace(",", ".")
            try:
                val = float(text)
                if val > 0:
                    result[0] = val
                    dlg.destroy()
            except ValueError:
                entry.select_range(0, tk.END)

        def cancel(event=None):
            dlg.destroy()

        btn_frame = tk.Frame(dlg)
        btn_frame.pack(padx=16, pady=(8, 16))
        tk.Button(btn_frame, text="Aceptar", width=10, command=confirm).pack(side=tk.LEFT, padx=4)
        tk.Button(btn_frame, text="Cancelar", width=10, command=cancel).pack(side=tk.LEFT, padx=4)

        dlg.bind("<Return>", confirm)
        dlg.bind("<KP_Enter>", confirm)
        dlg.bind("<Escape>", cancel)
        dlg.protocol("WM_DELETE_WINDOW", cancel)

        dlg.update_idletasks()
        dlg.minsize(dlg.winfo_reqwidth(), dlg.winfo_reqheight())
        rx = self.root.winfo_rootx() + (self.root.winfo_width() - dlg.winfo_reqwidth()) // 2
        ry = self.root.winfo_rooty() + (self.root.winfo_height() - dlg.winfo_reqheight()) // 2
        dlg.geometry(f"+{rx}+{ry}")
        dlg.transient(self.root)
        dlg.grab_set()
        entry.focus_set()

        dlg.wait_window()
        return result[0]

    def _ask_text(self) -> str | None:
        dlg = tk.Toplevel(self.root)
        dlg.title("Anotación")
        dlg.resizable(False, False)

        tk.Label(dlg, text="Texto:").pack(padx=16, pady=(16, 4))
        entry = tk.Entry(dlg, width=30, justify=tk.CENTER, font=("sans-serif", 14))
        entry.pack(padx=16, pady=4)

        result: list[str | None] = [None]

        def confirm(event=None):
            text = entry.get().strip()
            if text:
                result[0] = text
                dlg.destroy()

        def cancel(event=None):
            dlg.destroy()

        btn_frame = tk.Frame(dlg)
        btn_frame.pack(padx=16, pady=(8, 16))
        tk.Button(btn_frame, text="Aceptar", width=10, command=confirm).pack(side=tk.LEFT, padx=4)
        tk.Button(btn_frame, text="Cancelar", width=10, command=cancel).pack(side=tk.LEFT, padx=4)

        dlg.bind("<Return>", confirm)
        dlg.bind("<KP_Enter>", confirm)
        dlg.bind("<Escape>", cancel)
        dlg.protocol("WM_DELETE_WINDOW", cancel)

        dlg.update_idletasks()
        dlg.minsize(dlg.winfo_reqwidth(), dlg.winfo_reqheight())
        rx = self.root.winfo_rootx() + (self.root.winfo_width() - dlg.winfo_reqwidth()) // 2
        ry = self.root.winfo_rooty() + (self.root.winfo_height() - dlg.winfo_reqheight()) // 2
        dlg.geometry(f"+{rx}+{ry}")
        dlg.transient(self.root)
        dlg.grab_set()
        entry.focus_set()

        dlg.wait_window()
        return result[0]

    def _draw_all(self, img: Image.Image):
        for item in self.items:
            if item[0] == "cota":
                _, ax, ay, bx, by, label = item
                draw_cota(img, ax, ay, bx, by, label, self.font, self.escala)
            else:
                _, px, py, text = item
                draw_callout(img, px, py, text, self.font,
                             self.orig_w, self.orig_h, self.escala)

    def redraw(self):
        composed = self.original.copy()
        self._draw_all(composed)
        disp = composed.resize((self.disp_w, self.disp_h), Image.LANCZOS)
        self._tk_img = ImageTk.PhotoImage(disp)
        self.canvas.delete("img")
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self._tk_img, tags="img")
        self.canvas.tag_lower("img")

    def undo(self):
        if self.items:
            self.items.pop()
            self.redraw()
            self._update_status_idle()

    def save(self):
        salida = self.img_path.with_name(f"{self.img_path.stem}_acotada.png")
        composed = self.original.copy()
        self._draw_all(composed)
        composed.save(salida)
        self.status.config(text=f"Guardada: {salida}")
        print(f"✓ {salida}")


def main():
    p = argparse.ArgumentParser(
        description="Herramienta visual interactiva para acotar imágenes de producto.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("imagen", type=Path)
    p.add_argument("--unidad", default="cm", help="Unidad de medida (default: cm)")
    p.add_argument("--fondo", choices=["blanco", "transparente"], default="blanco",
                   help="Color de fondo (default: blanco)")
    p.add_argument("--margen", type=int, default=DEFAULT_MARGEN,
                   help=f"Margen alrededor de la imagen en px (default {DEFAULT_MARGEN})")
    p.add_argument("--escala", type=float, default=1.0,
                   help="Escala de líneas, flechas y texto (default 1.0)")
    args = p.parse_args()

    entrada = args.imagen.resolve()
    if not entrada.exists():
        print(f"No existe: {entrada}", file=sys.stderr)
        sys.exit(1)

    root = tk.Tk()
    AcotarApp(root, entrada, args.unidad, args.fondo, args.margen, args.escala)
    root.mainloop()


if __name__ == "__main__":
    main()
