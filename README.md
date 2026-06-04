# PDF Text & Image Extractor

Aplicación de escritorio para extraer texto e imágenes de archivos PDF, con dos modos de extracción y opciones de conversión de formato.

![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## Características

- **Dos modos de extracción** seleccionables desde la interfaz:
  - **Imágenes embebidas**: extrae las imágenes que el PDF lleva internamente.
  - **Páginas renderizadas**: convierte cada página completa en una imagen, igual que la vería un lector de PDF. Permite elegir la resolución en DPI.
- **Extracción de texto**: guarda el texto de todas las páginas en un archivo `.txt`, separado por sección por página (en ambos modos).
- **Conversión de formato**: convierte las imágenes extraídas a PNG, JPEG, BMP, TIFF o WEBP.
- **Interfaz gráfica** con barra de progreso, log en tiempo real y botón de cancelación.
- **Auto-instalación de dependencias** si no están presentes.

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
3. Selecciona el **modo de extracción**:
   - *Imágenes embebidas*: extrae las imágenes internas del PDF.
   - *Páginas renderizadas*: renderiza cada página como imagen. Aparece el selector de **Resolución (DPI)**.
4. Selecciona el formato de imagen de destino (opcional).
5. Pulsa **Extraer**.
6. Al terminar, usa **Abrir carpeta** para ver los resultados.

### Resoluciones disponibles (modo páginas renderizadas)

| DPI | Uso recomendado |
|-----|-----------------|
| 72  | Previsualización rápida |
| 96  | Pantalla estándar |
| 150 | Lectura en pantalla |
| 200 | Calidad media / OCR |
| 300 | Impresión / archivo |

### Estructura de salida

```
<nombre_pdf>_extracted/
├── <nombre_pdf>.txt        # Texto extraído, separado por páginas
└── images/
    ├── page1.png           # Modo páginas renderizadas
    ├── page2.png
    │   ...
    ├── page1_img1.png      # Modo imágenes embebidas
    ├── page1_img2.jpg
    └── ...
```

## Dependencias

| Paquete | Uso |
|---------|-----|
| [PyMuPDF](https://pymupdf.readthedocs.io/) | Lectura y renderizado de PDFs |
| [Pillow](https://python-pillow.org/) | Manipulación y conversión de imágenes |

## Licencia

Este proyecto está bajo la [Licencia MIT](LICENSE).
