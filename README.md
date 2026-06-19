# Media Center

Aplicación de escritorio local para trabajar con PDFs e imágenes, con soporte futuro para audio y video.

![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![PyQt6](https://img.shields.io/badge/PyQt6-6.6%2B-green)
![License](https://img.shields.io/badge/license-MIT-green)

## Características

### Módulo PDF

- **Tres modos de extracción** seleccionables desde la interfaz:
  - **Imágenes embebidas**: extrae las imágenes que el PDF lleva internamente.
  - **Páginas renderizadas**: convierte cada página completa en una imagen. Permite elegir la resolución en DPI.
  - **Markdown estructurado**: genera un archivo `.md` con el contenido del PDF, detectando encabezados (H1/H2/H3) por tamaño de fuente y negrita, reconstruyendo tablas en formato markdown e incrustando referencias a las imágenes.
- **Extracción de texto**: guarda el texto de todas las páginas en un `.txt`, separado por página.
- **Conversión de formato**: convierte las imágenes extraídas a PNG, JPEG, BMP, TIFF o WEBP.
- **Empaquetado CBZ**: comprime las imágenes en un archivo `.cbz` compatible con lectores de cómics.
- **Copia del PDF original**: opción para guardar el PDF fuente dentro de la carpeta de salida.
- **Procesamiento por lotes**: selecciona varios PDFs y extrae todos de una vez.

### General

- **Interfaz PyQt6** con barra de progreso, log en tiempo real y botón de cancelación.
- **Auto-instalación de dependencias** si no están presentes.
- Arquitectura modular: cada tipo de medio tiene su propio panel y procesador independientes.

## Requisitos

- Python 3.8 o superior

```bash
pip install -r requirements.txt
```

## Uso

```bash
python main.py
```

1. Selecciona el módulo en la barra lateral izquierda (**PDF**, Imagen, Audio, Video).
2. En el módulo PDF:
   - Selecciona uno o varios PDFs con los botones **Un archivo** / **Varios…**
   - Elige la carpeta de salida (se propone automáticamente una carpeta junto al PDF).
   - Selecciona el **modo de extracción**:
     - *Imágenes embebidas*: extrae las imágenes internas del PDF.
     - *Páginas renderizadas*: renderiza cada página como imagen. Aparece el selector de **Resolución (DPI)**.
     - *Markdown estructurado*: genera un `.md` con el contenido estructurado y las imágenes referenciadas.
   - Selecciona el formato de imagen de destino (no aplica en modo Markdown).
   - Activa **CBZ** para comprimir las imágenes en un archivo de cómic (no aplica en modo Markdown).
   - Activa **Guardar copia del PDF original** si quieres conservar el PDF fuente en la carpeta de salida.
   - Pulsa **Extraer**.
3. Al terminar, usa **Abrir carpeta** para ver los resultados.

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
├── <nombre_pdf>.txt        # Modos: imágenes embebidas y páginas renderizadas
├── <nombre_pdf>.md         # Modo: Markdown estructurado
└── images/
    ├── page1.png           # Modo páginas renderizadas
    ├── page1_img1.png      # Modos imágenes embebidas y Markdown
    └── ...
```

En modo por lotes, cada PDF genera su propia subcarpeta `<nombre_pdf>_extracted/` dentro de la carpeta de salida elegida.

## Estructura del proyecto

```
media-center/
├── main.py                      # Entry point
├── processors/
│   └── pdf.py                   # Lógica de extracción PDF (sin dependencias de UI)
├── ui/
│   ├── main_window.py           # Ventana principal con sidebar
│   ├── panels/
│   │   └── pdf_panel.py         # Panel de extracción PDF
│   └── widgets/
│       └── log_widget.py        # Área de log reutilizable
└── requirements.txt
```

## Dependencias

| Paquete | Uso |
|---------|-----|
| [PyQt6](https://doc.qt.io/qtforpython/) | Framework de interfaz gráfica |
| [PyMuPDF](https://pymupdf.readthedocs.io/) | Lectura y renderizado de PDFs |
| [Pillow](https://python-pillow.org/) | Manipulación y conversión de imágenes |

## Licencia

Este proyecto está bajo la [Licencia MIT](LICENSE).
