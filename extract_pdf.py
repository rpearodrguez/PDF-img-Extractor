import tkinter as tk
from tkinter import filedialog, scrolledtext, ttk
import threading
import zipfile
import shutil
import os
import sys

try:
    import fitz
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pymupdf"])
    import fitz

try:
    from PIL import Image
    import io
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow"])
    from PIL import Image
    import io

CONVERT_FORMATS = ["(keep original)", "PNG", "JPEG", "BMP", "TIFF", "WEBP"]
PIL_FORMAT_MAP = {
    "PNG":  ("PNG",  "png"),
    "JPEG": ("JPEG", "jpg"),
    "BMP":  ("BMP",  "bmp"),
    "TIFF": ("TIFF", "tif"),
    "WEBP": ("WEBP", "webp"),
}

EXTRACT_MODES = [
    ("images", "Imágenes embebidas del PDF"),
    ("render", "Páginas renderizadas como imágenes  ✦"),
]
_EXTRACT_LABELS   = [label for _, label in EXTRACT_MODES]
_EXTRACT_BY_LABEL = {label: value for value, label in EXTRACT_MODES}

RENDER_DPI_OPTIONS = [
    "72  – Previsualización rápida",
    "96  – Pantalla estándar",
    "150 – Lectura en pantalla",
    "200 – Calidad media / OCR",
    "300 – Impresión / archivo",
]


# ── helpers de imagen ──────────────────────────────────────────────────────

def convert_image(src_bytes: bytes, target_format: str) -> tuple:
    fmt, ext = PIL_FORMAT_MAP[target_format]
    img = Image.open(io.BytesIO(src_bytes))
    if fmt == "JPEG" and img.mode in ("RGBA", "P", "LA"):
        img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue(), ext


def pack_cbz(output_dir: str, cbz_name: str, log) -> bool:
    images_dir = os.path.join(output_dir, "images")
    if not os.path.isdir(images_dir):
        return False

    image_files = sorted(
        f for f in os.listdir(images_dir)
        if os.path.isfile(os.path.join(images_dir, f))
    )
    if not image_files:
        return False

    cbz_path = os.path.join(output_dir, f"{cbz_name}.cbz")
    with zipfile.ZipFile(cbz_path, "w", zipfile.ZIP_STORED) as zf:
        for fname in image_files:
            zf.write(os.path.join(images_dir, fname), fname)

    shutil.rmtree(images_dir)
    log(f"CBZ → {cbz_path}")
    return True


# ── extracción de imágenes embebidas ───────────────────────────────────────

def extract_pdf(pdf_path, output_dir, convert_fmt,
                log, progress_var, progress_bar, stop_event=None):
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    text_lines  = []
    image_count = 0

    os.makedirs(output_dir, exist_ok=True)
    images_dir = os.path.join(output_dir, "images")
    os.makedirs(images_dir, exist_ok=True)

    do_convert = convert_fmt != "(keep original)"

    for page_num, page in enumerate(doc):
        if stop_event and stop_event.is_set():
            log("Extracción detenida por el usuario.")
            break
        pn = page_num + 1
        log(f"Procesando página {pn}/{total_pages}...")
        progress_var.set(int(pn / total_pages * 100))
        progress_bar.update_idletasks()

        text_lines.append(f"--- Página {pn} ---\n{page.get_text()}")

        for idx, img_ref in enumerate(page.get_images(full=True)):
            base = doc.extract_image(img_ref[0])
            ext  = (base["ext"] or "bin").strip(".")
            data = base["image"]
            if do_convert:
                try:
                    data, ext = convert_image(data, convert_fmt)
                except Exception as e:
                    log(f"  Advertencia: conversión falló (p.{pn} img {idx+1}): {e}")
            path = os.path.join(images_dir, f"page{pn}_img{idx+1}.{ext}")
            with open(path, "wb") as f:
                f.write(data)
            image_count += 1

    doc.close()

    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    text_path = os.path.join(output_dir, f"{base_name}.txt")
    with open(text_path, "w", encoding="utf-8") as f:
        f.write("\n\n".join(text_lines))

    log(f"Listo! {total_pages} páginas, {image_count} imagen(es) guardadas.")
    if do_convert and image_count:
        log(f"  Formato: {convert_fmt}.")
    log(f"Texto → {text_path}")
    if not image_count:
        log("No se encontraron imágenes en este PDF.")

    return base_name


# ── renderizado de páginas completas ──────────────────────────────────────

def render_pages(pdf_path, output_dir, convert_fmt, dpi,
                 log, progress_var, progress_bar, stop_event=None):
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    text_lines  = []

    os.makedirs(output_dir, exist_ok=True)
    images_dir = os.path.join(output_dir, "images")
    os.makedirs(images_dir, exist_ok=True)

    scale      = int(dpi) / 72
    matrix     = fitz.Matrix(scale, scale)
    do_convert = convert_fmt != "(keep original)"

    for page_num, page in enumerate(doc):
        if stop_event and stop_event.is_set():
            log("Extracción detenida por el usuario.")
            break
        pn = page_num + 1
        log(f"Renderizando página {pn}/{total_pages}...")
        progress_var.set(int(pn / total_pages * 100))
        progress_bar.update_idletasks()

        text_lines.append(f"--- Página {pn} ---\n{page.get_text()}")

        pix  = page.get_pixmap(matrix=matrix, alpha=False)
        data = pix.tobytes("png")
        ext  = "png"

        if do_convert:
            try:
                data, ext = convert_image(data, convert_fmt)
            except Exception as e:
                log(f"  Advertencia: conversión falló en p.{pn}: {e}")

        path = os.path.join(images_dir, f"page{pn}.{ext}")
        with open(path, "wb") as f:
            f.write(data)

    doc.close()

    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    text_path = os.path.join(output_dir, f"{base_name}.txt")
    with open(text_path, "w", encoding="utf-8") as f:
        f.write("\n\n".join(text_lines))

    log(f"Listo! {total_pages} páginas renderizadas a {dpi} DPI.")
    if do_convert:
        log(f"  Formato: {convert_fmt}.")
    log(f"Texto → {text_path}")

    return base_name


# ── interfaz principal ─────────────────────────────────────────────────────

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PDF Text & Image Extractor")
        self.resizable(False, False)
        self._stop_event   = threading.Event()
        self._last_out_dir = None
        self._pdf_files    = []
        self._build_ui()

    def _build_ui(self):
        pad = {"padx": 8, "pady": 4}

        # ── fila 0: archivo(s) PDF
        tk.Label(self, text="Archivo(s) PDF:").grid(row=0, column=0, sticky="e", **pad)
        self.pdf_var = tk.StringVar()
        self._pdf_entry = tk.Entry(self, textvariable=self.pdf_var, width=44,
                                   state="readonly", readonlybackground="white")
        self._pdf_entry.grid(row=0, column=1, **pad)
        btn_pdf_frame = tk.Frame(self)
        btn_pdf_frame.grid(row=0, column=2, **pad)
        tk.Button(btn_pdf_frame, text="Un archivo",
                  command=self._browse_pdf_single).pack(side="left", padx=(0, 2))
        tk.Button(btn_pdf_frame, text="Varios…",
                  command=self._browse_pdf_multi).pack(side="left")

        # ── fila 1: carpeta de salida
        tk.Label(self, text="Carpeta de salida:").grid(row=1, column=0, sticky="e", **pad)
        self.out_var = tk.StringVar()
        tk.Entry(self, textvariable=self.out_var, width=44).grid(row=1, column=1, **pad)
        tk.Button(self, text="Buscar…", command=self._browse_output).grid(row=1, column=2, **pad)

        # ── fila 2: modo de extracción
        tk.Label(self, text="Modo de extracción:").grid(row=2, column=0, sticky="e", **pad)
        self.extract_mode_var = tk.StringVar(value=_EXTRACT_LABELS[0])
        extract_cb = ttk.Combobox(self, textvariable=self.extract_mode_var,
                                  values=_EXTRACT_LABELS, state="readonly", width=36)
        extract_cb.grid(row=2, column=1, columnspan=2, sticky="w", **pad)
        extract_cb.bind("<<ComboboxSelected>>", self._on_extract_mode_change)

        # ── fila 3: convertir imágenes a
        tk.Label(self, text="Convertir imágenes a:").grid(row=3, column=0, sticky="e", **pad)
        self.fmt_var = tk.StringVar(value=CONVERT_FORMATS[0])
        ttk.Combobox(self, textvariable=self.fmt_var, values=CONVERT_FORMATS,
                     state="readonly", width=18).grid(row=3, column=1, sticky="w", **pad)

        # ── fila 4: resolución DPI (solo modo render, oculto por defecto)
        self._dpi_label = tk.Label(self, text="Resolución (DPI):")
        self._dpi_label.grid(row=4, column=0, sticky="e", **pad)
        self._dpi_label.grid_remove()
        self.dpi_var = tk.StringVar(value=RENDER_DPI_OPTIONS[2])
        self._dpi_cb = ttk.Combobox(self, textvariable=self.dpi_var,
                                    values=RENDER_DPI_OPTIONS, state="readonly", width=28)
        self._dpi_cb.grid(row=4, column=1, sticky="w", **pad)
        self._dpi_cb.grid_remove()

        # ── fila 5: opción CBZ
        self.cbz_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            self, text="Comprimir imágenes en CBZ  (reemplaza la carpeta images/)",
            variable=self.cbz_var, anchor="w",
        ).grid(row=5, column=0, columnspan=3, sticky="w", padx=10, pady=(0, 2))

        # ── fila 6: barra de progreso
        self.progress_var = tk.IntVar(value=0)
        self.progress_bar = ttk.Progressbar(self, variable=self.progress_var,
                                             maximum=100, length=420)
        self.progress_bar.grid(row=6, column=0, columnspan=3, padx=8, pady=6)

        # ── fila 7: botones
        btn_row = tk.Frame(self)
        btn_row.grid(row=7, column=0, columnspan=3, pady=6)

        self.btn_extract = tk.Button(
            btn_row, text="Extraer", width=14,
            bg="#0078d4", fg="white", font=("Segoe UI", 10, "bold"),
            command=self._start_extract,
        )
        self.btn_extract.pack(side="left", padx=6)

        self.btn_stop = tk.Button(
            btn_row, text="Detener", width=10,
            bg="#c42b1c", fg="white", font=("Segoe UI", 10, "bold"),
            state="disabled", command=self._stop_extract,
        )
        self.btn_stop.pack(side="left", padx=6)

        self.btn_open = tk.Button(
            btn_row, text="Abrir carpeta", width=12,
            font=("Segoe UI", 10), state="disabled",
            command=self._open_folder,
        )
        self.btn_open.pack(side="left", padx=6)

        # ── fila 8: área de log
        self.log_area = scrolledtext.ScrolledText(
            self, width=60, height=12, state="disabled", font=("Consolas", 9)
        )
        self.log_area.grid(row=8, column=0, columnspan=3, padx=8, pady=(0, 8))

    # ── eventos ───────────────────────────────────────────────────────────────

    def _on_extract_mode_change(self, *_):
        mode = _EXTRACT_BY_LABEL.get(self.extract_mode_var.get(), "images")
        if mode == "render":
            self._dpi_label.grid()
            self._dpi_cb.grid()
        else:
            self._dpi_label.grid_remove()
            self._dpi_cb.grid_remove()

    def _set_single_pdf(self, path):
        self._pdf_files = [path]
        self.pdf_var.set(path)
        base = os.path.splitext(os.path.basename(path))[0]
        self.out_var.set(os.path.join(os.path.dirname(path), f"{base}_extracted"))
        self._last_out_dir = None
        self.btn_open.config(state="disabled")

    def _browse_pdf_single(self):
        path = filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
        if path:
            self._set_single_pdf(path)

    def _browse_pdf_multi(self):
        paths = filedialog.askopenfilenames(filetypes=[("PDF Files", "*.pdf")])
        if not paths:
            return
        if len(paths) == 1:
            self._set_single_pdf(paths[0])
        else:
            self._pdf_files = list(paths)
            self.pdf_var.set(f"({len(paths)} archivos seleccionados)")
            self.out_var.set(os.path.dirname(paths[0]))
            self._last_out_dir = None
            self.btn_open.config(state="disabled")

    def _browse_output(self):
        path = filedialog.askdirectory()
        if path:
            self.out_var.set(path)

    def _open_folder(self):
        if self._last_out_dir and os.path.isdir(self._last_out_dir):
            os.startfile(self._last_out_dir)

    def _stop_extract(self):
        self._stop_event.set()
        self.btn_stop.config(state="disabled")

    def _log(self, message: str):
        self.log_area.config(state="normal")
        self.log_area.insert("end", message + "\n")
        self.log_area.see("end")
        self.log_area.config(state="disabled")

    def _start_extract(self):
        if not self._pdf_files:
            self._log("ERROR: Por favor seleccione al menos un archivo PDF.")
            return

        out_dir = self.out_var.get().strip()
        if not out_dir:
            self._log("ERROR: Por favor seleccione una carpeta de salida.")
            return

        extract_mode = _EXTRACT_BY_LABEL.get(self.extract_mode_var.get(), "images")
        convert_fmt  = self.fmt_var.get()
        dpi          = self.dpi_var.get().split()[0]
        make_cbz     = self.cbz_var.get()
        pdf_files    = list(self._pdf_files)
        batch        = len(pdf_files) > 1

        self._stop_event.clear()
        self.btn_extract.config(state="disabled")
        self.btn_stop.config(state="normal")
        self.btn_open.config(state="disabled")
        self.progress_var.set(0)

        if batch:
            self._log(f"Iniciando extracción por lotes: {len(pdf_files)} archivos.")
        else:
            self._log(f"Iniciando extracción: {os.path.basename(pdf_files[0])}")

        if extract_mode == "render":
            self._log(f"Modo: páginas renderizadas a {dpi} DPI.")
        if convert_fmt != "(keep original)":
            self._log(f"Imágenes se convertirán a {convert_fmt}.")
        if make_cbz:
            self._log("Salida: CBZ (la carpeta images/ se eliminará al finalizar).")

        def run():
            last_dir = out_dir
            for i, pdf_path in enumerate(pdf_files):
                if self._stop_event.is_set():
                    break

                stem = os.path.splitext(os.path.basename(pdf_path))[0]

                if batch:
                    file_out = os.path.join(out_dir, f"{stem}_extracted")
                    self._log(f"\n── Archivo {i+1}/{len(pdf_files)}: {os.path.basename(pdf_path)}")
                    last_dir = out_dir
                else:
                    file_out = out_dir

                self.progress_var.set(0)
                try:
                    if extract_mode == "render":
                        base_name = render_pages(
                            pdf_path, file_out, convert_fmt, dpi,
                            self._log, self.progress_var, self.progress_bar,
                            stop_event=self._stop_event,
                        )
                    else:
                        base_name = extract_pdf(
                            pdf_path, file_out, convert_fmt,
                            self._log, self.progress_var, self.progress_bar,
                            stop_event=self._stop_event,
                        )

                    if make_cbz and not self._stop_event.is_set():
                        pack_cbz(file_out, base_name, self._log)

                except Exception as e:
                    self._log(f"ERROR en {os.path.basename(pdf_path)}: {e}")

            if batch:
                self._log(f"\nProceso por lotes finalizado.")

            self.btn_extract.config(state="normal")
            self.btn_stop.config(state="disabled")
            if os.path.isdir(last_dir):
                self._last_out_dir = last_dir
                self.btn_open.config(state="normal")

        threading.Thread(target=run, daemon=True).start()


if __name__ == "__main__":
    app = App()
    app.mainloop()
