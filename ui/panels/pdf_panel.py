import os
import shutil
import threading

from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QPushButton, QComboBox, QCheckBox,
    QProgressBar, QFileDialog,
)
from PyQt6.QtGui import QFont

from processors.pdf import (
    CONVERT_FORMATS, pack_cbz, extract_pdf, render_pages, extract_markdown,
)
from ui.widgets.log_widget import LogWidget


EXTRACT_MODES = [
    ("images",   "Imágenes embebidas del PDF"),
    ("render",   "Páginas renderizadas"),
    ("markdown", "Markdown estructurado"),
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


# ── worker thread ─────────────────────────────────────────────────────────

class _PdfWorker(QThread):
    log_message        = pyqtSignal(str)
    progress_changed   = pyqtSignal(int)
    file_count_changed = pyqtSignal(str)
    finished           = pyqtSignal(str)

    def __init__(self, cfg: dict):
        super().__init__()
        self._cfg  = cfg
        self._stop = threading.Event()

    def stop(self):
        self._stop.set()

    def run(self):
        cfg      = self._cfg
        files    = cfg["pdf_files"]
        out_dir  = cfg["out_dir"]
        mode     = cfg["mode"]
        fmt      = cfg["convert_fmt"]
        dpi      = cfg["dpi"]
        make_cbz = cfg["make_cbz"]
        copy_pdf = cfg["copy_pdf"]
        batch    = len(files) > 1
        log      = self.log_message.emit
        prog     = self.progress_changed.emit
        last_dir = out_dir

        if batch:
            log(f"Iniciando extracción por lotes: {len(files)} archivos.")
        else:
            log(f"Iniciando extracción: {os.path.basename(files[0])}")

        if mode == "render":
            log(f"Modo: páginas renderizadas a {dpi} DPI.")
        elif mode == "markdown":
            log("Modo: Markdown estructurado.")
        if fmt != "(keep original)" and mode != "markdown":
            log(f"Imágenes se convertirán a {fmt}.")
        if make_cbz and mode != "markdown":
            log("Salida: CBZ.")

        for i, pdf_path in enumerate(files):
            if self._stop.is_set():
                break

            stem = os.path.splitext(os.path.basename(pdf_path))[0]

            if batch:
                self.file_count_changed.emit(f"Archivo {i + 1} / {len(files)}")
                file_out = os.path.join(out_dir, f"{stem}_extracted")
                log(f"\n── Archivo {i + 1}/{len(files)}: {os.path.basename(pdf_path)}")
                last_dir = out_dir
            else:
                file_out = out_dir

            prog(0)

            try:
                if mode == "render":
                    base = render_pages(pdf_path, file_out, fmt, dpi, log, prog, self._stop)
                elif mode == "markdown":
                    base = extract_markdown(pdf_path, file_out, log, prog, self._stop)
                else:
                    base = extract_pdf(pdf_path, file_out, fmt, log, prog, self._stop)

                if make_cbz and mode != "markdown" and not self._stop.is_set():
                    pack_cbz(file_out, base, log)

                if copy_pdf and not self._stop.is_set():
                    dest = os.path.join(file_out, os.path.basename(pdf_path))
                    shutil.copy2(pdf_path, dest)
                    log(f"PDF original → {dest}")

            except Exception as e:
                log(f"ERROR en {os.path.basename(pdf_path)}: {e}")

        if batch:
            log("\nProceso por lotes finalizado.")

        self.file_count_changed.emit("")
        self.finished.emit(last_dir if os.path.isdir(last_dir) else "")


# ── panel ─────────────────────────────────────────────────────────────────

class PdfPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker    = None
        self._pdf_files = []
        self._last_dir  = None
        self._build_ui()

    def _build_ui(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(20, 20, 20, 20)
        main.setSpacing(12)

        # ── archivos y carpeta de salida ──
        form = QFormLayout()
        form.setSpacing(8)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        pdf_row = QHBoxLayout()
        self._pdf_edit = QLineEdit()
        self._pdf_edit.setReadOnly(True)
        self._pdf_edit.setPlaceholderText("Seleccionar archivo(s) PDF…")
        pdf_row.addWidget(self._pdf_edit, 1)
        btn_pdf = QPushButton("Seleccionar…")
        btn_pdf.clicked.connect(self._browse_pdf)
        pdf_row.addWidget(btn_pdf)
        form.addRow("Archivo(s) PDF:", pdf_row)

        out_row = QHBoxLayout()
        self._out_edit = QLineEdit()
        self._out_edit.setPlaceholderText("Carpeta de salida…")
        out_row.addWidget(self._out_edit, 1)
        btn_out = QPushButton("Buscar…")
        btn_out.clicked.connect(self._browse_output)
        out_row.addWidget(btn_out)
        form.addRow("Carpeta de salida:", out_row)

        main.addLayout(form)

        # ── opciones de extracción ──
        opts = QFormLayout()
        opts.setSpacing(8)
        opts.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._mode_combo = QComboBox()
        self._mode_combo.addItems(_EXTRACT_LABELS)
        self._mode_combo.currentTextChanged.connect(self._on_mode_change)
        opts.addRow("Modo de extracción:", self._mode_combo)

        self._fmt_label = QLabel("Convertir imágenes a:")
        self._fmt_combo = QComboBox()
        self._fmt_combo.addItems(CONVERT_FORMATS)
        opts.addRow(self._fmt_label, self._fmt_combo)

        self._dpi_label = QLabel("Resolución (DPI):")
        self._dpi_combo = QComboBox()
        self._dpi_combo.addItems(RENDER_DPI_OPTIONS)
        self._dpi_combo.setCurrentIndex(2)
        opts.addRow(self._dpi_label, self._dpi_combo)
        self._dpi_label.hide()
        self._dpi_combo.hide()

        main.addLayout(opts)

        # ── checkboxes ──
        chk_row = QHBoxLayout()
        self._cbz_check  = QCheckBox("Comprimir imágenes en CBZ")
        self._copy_check = QCheckBox("Guardar copia del PDF original")
        chk_row.addWidget(self._cbz_check)
        chk_row.addWidget(self._copy_check)
        chk_row.addStretch()
        main.addLayout(chk_row)

        # ── barra de progreso ──
        prog_row = QHBoxLayout()
        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        prog_row.addWidget(self._progress, 1)
        self._file_count_label = QLabel("")
        self._file_count_label.setFixedWidth(150)
        prog_row.addWidget(self._file_count_label)
        main.addLayout(prog_row)

        # ── botones de acción ──
        btn_row = QHBoxLayout()

        self._btn_extract = QPushButton("Extraer")
        self._btn_extract.setStyleSheet(
            "background:#0078d4; color:white; font-weight:bold; padding:6px 24px; border-radius:4px;"
        )
        self._btn_extract.clicked.connect(self._start_extract)

        self._btn_stop = QPushButton("Detener")
        self._btn_stop.setStyleSheet(
            "background:#c42b1c; color:white; font-weight:bold; padding:6px 24px; border-radius:4px;"
        )
        self._btn_stop.setEnabled(False)
        self._btn_stop.clicked.connect(self._stop_extract)

        self._btn_open = QPushButton("Abrir carpeta")
        self._btn_open.setEnabled(False)
        self._btn_open.clicked.connect(self._open_folder)

        btn_row.addWidget(self._btn_extract)
        btn_row.addWidget(self._btn_stop)
        btn_row.addWidget(self._btn_open)
        btn_row.addStretch()
        main.addLayout(btn_row)

        # ── área de log ──
        self._log = LogWidget()
        main.addWidget(self._log, 1)

    # ── slots ──

    def _on_mode_change(self, label: str):
        mode = _EXTRACT_BY_LABEL.get(label, "images")
        is_render   = mode == "render"
        is_markdown = mode == "markdown"
        self._dpi_label.setVisible(is_render)
        self._dpi_combo.setVisible(is_render)
        self._fmt_label.setVisible(not is_markdown)
        self._fmt_combo.setVisible(not is_markdown)
        self._cbz_check.setEnabled(not is_markdown)

    def _set_single_pdf(self, path: str):
        self._pdf_files = [path]
        self._pdf_edit.setText(path)
        stem = os.path.splitext(os.path.basename(path))[0]
        self._out_edit.setText(os.path.join(os.path.dirname(path), f"{stem}_extracted"))
        self._last_dir = None
        self._btn_open.setEnabled(False)

    def _browse_pdf(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Seleccionar PDF(s)", "", "PDF Files (*.pdf)")
        if not paths:
            return
        if len(paths) == 1:
            self._set_single_pdf(paths[0])
        else:
            self._pdf_files = list(paths)
            self._pdf_edit.setText(f"({len(paths)} archivos seleccionados)")
            self._out_edit.setText(os.path.dirname(paths[0]))
            self._last_dir = None
            self._btn_open.setEnabled(False)

    def _browse_output(self):
        path = QFileDialog.getExistingDirectory(self, "Carpeta de salida")
        if path:
            self._out_edit.setText(path)

    def _open_folder(self):
        if self._last_dir and os.path.isdir(self._last_dir):
            os.startfile(self._last_dir)

    def _stop_extract(self):
        if self._worker:
            self._worker.stop()
        self._btn_stop.setEnabled(False)

    def _start_extract(self):
        if not self._pdf_files:
            self._log.append_message("ERROR: Por favor seleccione al menos un archivo PDF.")
            return

        out_dir = self._out_edit.text().strip()
        if not out_dir:
            self._log.append_message("ERROR: Por favor seleccione una carpeta de salida.")
            return

        mode = _EXTRACT_BY_LABEL.get(self._mode_combo.currentText(), "images")

        cfg = {
            "pdf_files":   list(self._pdf_files),
            "out_dir":     out_dir,
            "mode":        mode,
            "convert_fmt": self._fmt_combo.currentText(),
            "dpi":         self._dpi_combo.currentText().split()[0],
            "make_cbz":    self._cbz_check.isChecked(),
            "copy_pdf":    self._copy_check.isChecked(),
        }

        self._log.clear_log()
        self._worker = _PdfWorker(cfg)
        self._worker.log_message.connect(self._log.append_message)
        self._worker.progress_changed.connect(self._progress.setValue)
        self._worker.file_count_changed.connect(self._file_count_label.setText)
        self._worker.finished.connect(self._on_finished)
        self._worker.start()

        self._btn_extract.setEnabled(False)
        self._btn_stop.setEnabled(True)
        self._btn_open.setEnabled(False)
        self._progress.setValue(0)

    def _on_finished(self, last_dir: str):
        self._btn_extract.setEnabled(True)
        self._btn_stop.setEnabled(False)
        if last_dir:
            self._last_dir = last_dir
            self._btn_open.setEnabled(True)
