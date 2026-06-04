# PDF Text & Image Extractor

Aplicación de escritorio para extraer texto e imágenes de archivos PDF, con opciones de conversión de formato y combinación de imágenes por página.

![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## Características

- **Extracción de texto**: guarda el texto de todas las páginas en un archivo `.txt`, separado por sección por página.
- **Extracción de imágenes**: extrae las imágenes embebidas del PDF.
- **Conversión de formato**: convierte las imágenes extraídas a PNG, JPEG, BMP, TIFF o WEBP.
- **Modos de combinación de imágenes por página**:
  - **Separadas** (por defecto): guarda cada imagen como archivo independiente.
  - **Renderizar página completa**: reconstruye la página usando el motor de renderizado del PDF (recomendado para libros escaneados).
  - **Horizontal**: combina las imágenes de la página en una sola fila.
  - **Vertical**: apila las imágenes de la página en una sola columna.
- **Interfaz gráfica** con barra de progreso, log en tiempo real y botón de cancelación.
- **Auto-instalación de dependencias** si no están presentes.

## Capturas de pantalla

> _Agrega aquí capturas de pantalla de la aplicación._

## Requisitos

- Python 3.8 o superior
- Las dependencias se instalan automáticamente al ejecutar el script, o manualmente:

```bash
pip install -r requirements.txt
```

## Uso

```bash
python extract_pdf.py
```

1. Selecciona el archivo PDF con el botón **Buscar…**.
2. Elige la carpeta de salida (se propone automáticamente una carpeta junto al PDF).
3. Selecciona el formato de imagen de destino (opcional).
4. Elige el modo de combinación de imágenes (opcional).
5. Pulsa **Extraer**.
6. Al terminar, usa **Abrir carpeta** para ver los resultados.

### Estructura de salida

```
<nombre_pdf>_extracted/
├── <nombre_pdf>.txt       # Texto extraído, separado por páginas
└── images/
    ├── page1_img1.png
    ├── page1_img2.jpg
    ├── page2_merged.png   # Si se usa modo combinación
    └── ...
```

## Dependencias

| Paquete | Uso |
|---------|-----|
| [PyMuPDF](https://pymupdf.readthedocs.io/) | Lectura y renderizado de PDFs |
| [Pillow](https://python-pillow.org/) | Manipulación y conversión de imágenes |

## Licencia

Este proyecto está bajo la [Licencia MIT](LICENSE).
