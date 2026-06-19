import io
import os
import re
import sys
import shutil
import zipfile
from collections import Counter

try:
    import fitz
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pymupdf"])
    import fitz

try:
    from PIL import Image
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow"])
    from PIL import Image


CONVERT_FORMATS = ["(keep original)", "PNG", "JPEG", "BMP", "TIFF", "WEBP"]

_PIL_FORMAT_MAP = {
    "PNG":  ("PNG",  "png"),
    "JPEG": ("JPEG", "jpg"),
    "BMP":  ("BMP",  "bmp"),
    "TIFF": ("TIFF", "tif"),
    "WEBP": ("WEBP", "webp"),
}

_BULLET_CHARS = "●•◆▪▸▶‣⁃"


# ── helpers ────────────────────────────────────────────────────────────────

def _overlaps_any(bb: tuple, bboxes: list) -> bool:
    bx0, by0, bx1, by1 = bb
    for tx0, ty0, tx1, ty1 in bboxes:
        if bx0 < tx1 and bx1 > tx0 and by0 < ty1 and by1 > ty0:
            return True
    return False


def _format_lines(lines: list) -> str:
    result = []
    for line in lines:
        s = line.strip()
        if s and s[0] in _BULLET_CHARS:
            result.append("- " + s[1:].strip())
        else:
            result.append(line)
    return "\n".join(result)


def _rows_to_md_table(rows: list) -> str:
    def _cell(v):
        if v is None:
            return ""
        s = str(v).strip()
        s = re.sub(r"(?m)^\s*[●•◆▪▸▶‣⁃]\s*", "· ", s)
        return " ".join(s.split())

    cleaned = [[_cell(c) for c in row] for row in rows]
    if not cleaned:
        return ""
    ncols = max(len(r) for r in cleaned)
    cleaned = [r + [""] * (ncols - len(r)) for r in cleaned]
    sep   = "| " + " | ".join(["---"] * ncols) + " |"
    lines = ["| " + " | ".join(cleaned[0]) + " |", sep]
    lines += ["| " + " | ".join(row) + " |" for row in cleaned[1:]]
    return "\n".join(lines)


def convert_image(src_bytes: bytes, target_format: str) -> tuple:
    fmt, ext = _PIL_FORMAT_MAP[target_format]
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


# ── extracción de imágenes embebidas ──────────────────────────────────────

def extract_pdf(pdf_path, output_dir, convert_fmt,
                log, progress_cb, stop_event=None):
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
        progress_cb(int(pn / total_pages * 100))

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
                 log, progress_cb, stop_event=None):
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
        progress_cb(int(pn / total_pages * 100))

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


# ── extracción a markdown estructurado ────────────────────────────────────

def extract_markdown(pdf_path, output_dir, log, progress_cb, stop_event=None):
    doc = fitz.open(pdf_path)
    total_pages = len(doc)

    os.makedirs(output_dir, exist_ok=True)
    images_dir = os.path.join(output_dir, "images")
    os.makedirs(images_dir, exist_ok=True)

    # Primera pasada: detectar tamaño de fuente dominante (= cuerpo de texto)
    all_sizes = []
    for page in doc:
        for block in page.get_text("dict")["blocks"]:
            if block["type"] == 0:
                for line in block["lines"]:
                    for span in line["spans"]:
                        if span["text"].strip():
                            all_sizes.append(round(span["size"], 1))

    body_size = Counter(all_sizes).most_common(1)[0][0] if all_sizes else 11.0

    md_parts    = []
    image_count = 0
    seen_xrefs  = set()

    for page_num, page in enumerate(doc):
        if stop_event and stop_event.is_set():
            log("Extracción detenida por el usuario.")
            break
        pn = page_num + 1
        log(f"Procesando página {pn}/{total_pages}...")
        progress_cb(int(pn / total_pages * 100))

        img_map = {}
        for idx, img_ref in enumerate(page.get_images(full=True)):
            xref = img_ref[0]
            if xref in seen_xrefs:
                continue
            seen_xrefs.add(xref)
            base_img = doc.extract_image(xref)
            ext  = (base_img["ext"] or "bin").strip(".")
            fname = f"page{pn}_img{idx + 1}.{ext}"
            with open(os.path.join(images_dir, fname), "wb") as f:
                f.write(base_img["image"])
            img_map[xref] = fname
            image_count += 1

        # strategy="lines" detecta tablas con bordes reales.
        # strategy="text" produce celdas rotas en PDFs con bordes de color/redondeados.
        try:
            tables = page.find_tables(strategy="lines").tables
        except Exception:
            tables = []
        table_bboxes = [tbl.bbox for tbl in tables]

        page_width = page.rect.width
        page_mid   = page_width / 2

        def _col(bbox):
            if (bbox[2] - bbox[0]) > page_width * 0.6:
                return 0
            return 0 if (bbox[0] + bbox[2]) / 2 <= page_mid else 1

        items = []

        for tbl in tables:
            rows = tbl.extract()
            if rows:
                items.append((tbl.bbox[1], _col(tbl.bbox), "table", rows))

        for block in page.get_text("dict")["blocks"]:
            bb = block["bbox"]

            if block["type"] == 1:
                xref = block.get("xref", 0)
                if xref in img_map:
                    items.append((bb[1], _col(bb), "img", img_map[xref]))
                continue

            if _overlaps_any(bb, table_bboxes):
                continue

            lines_text  = []
            block_sizes = []
            is_bold     = False

            for line in block["lines"]:
                spans_text = []
                for span in line["spans"]:
                    span_text = span["text"]
                    if not span_text.strip():
                        continue
                    block_sizes.append(round(span["size"], 1))
                    if span["flags"] & 16:
                        is_bold = True
                    spans_text.append(span_text)
                if spans_text:
                    lines_text.append("".join(spans_text))

            text = _format_lines(lines_text)
            if text.strip():
                avg_size = sum(block_sizes) / len(block_sizes) if block_sizes else body_size
                ratio    = avg_size / body_size if body_size > 0 else 1.0
                items.append((bb[1], _col(bb), "text", (text, ratio, is_bold)))

        items.sort(key=lambda x: (x[1], x[0]))
        for _, _c, kind, content in items:
            if kind == "table":
                md_parts.append(_rows_to_md_table(content) + "\n")
            elif kind == "img":
                md_parts.append(f"![imagen](images/{content})\n")
            else:
                text, ratio, is_bold = content
                block_lines = text.split("\n")
                first_line  = block_lines[0]
                rest        = "\n".join(block_lines[1:]).strip() if len(block_lines) > 1 else ""

                single_bold_heading = (
                    is_bold
                    and len(block_lines) == 1
                    and len(first_line) < 100
                    and not first_line.startswith("- ")
                )

                if ratio >= 1.8:
                    md_parts.append(f"# {first_line}\n")
                elif ratio >= 1.4:
                    md_parts.append(f"## {first_line}\n")
                elif ratio >= 1.15 or (is_bold and ratio >= 1.05) or single_bold_heading:
                    md_parts.append(f"### {first_line}\n")
                else:
                    md_parts.append(f"{text}\n")
                    continue

                if rest:
                    md_parts.append(f"{rest}\n")

    doc.close()

    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    md_path = os.path.join(output_dir, f"{base_name}.md")
    raw = re.sub(r"\n{3,}", "\n\n", "\n".join(md_parts)).strip()
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(raw + "\n")

    log(f"Listo! {total_pages} páginas procesadas.")
    log(f"Markdown → {md_path}")
    if image_count:
        log(f"  {image_count} imagen(es) guardadas en images/")
    else:
        log("No se encontraron imágenes embebidas.")

    return base_name
