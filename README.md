# Puzzly

> Turn any picture into a printable jigsaw or grid puzzle.

**Puzzly** is a small Flask web app that turns your photos into cut-and-play
puzzles for kids. Pick a picture, choose a style and size, preview live, and
export a print-ready PDF — scattered pieces, a one-page cut-in-place puzzle, a
reference sheet, and a framed placement template.

The interface is built with a **Vintage Puzzle Studio** theme (warm cream,
mahogany, sage, gold) and **shadcn/ui-inspired** components styled with Tailwind CSS.

![Puzzly](https://img.shields.io/badge/license-MIT-blue.svg)

## Features
- Upload images (JPG, PNG, WEBP, BMP, GIF) or use pictures from the project folder
- Two cut styles: simple **Grid** or interlocking **Jigsaw** pieces
- Adjustable piece count (rows × columns) with difficulty presets
- Customizable cut-line thickness, paper size (A4 / Letter / A3), and layout
- Live preview with a rounded physical puzzle-board frame
- Choose exactly which PDF pages to include:
  - **Framed puzzle board** — the picture with its frame and cut lines (first page)
  - **Cut-out pieces** — scattered to cut, or one printable page
  - **Reference sheet** — the solved picture
  - **Placement template** — a white board with piece outlines
- Export only the pages you tick (save a single page, or the whole bundle)

## Tech stack
- **Backend:** Python 3.10+, Flask
- **Imaging:** Pillow (piece generation, framing, previews)
- **PDF:** fpdf2
- **Frontend:** Vanilla JS + Tailwind CSS (via CDN), shadcn/ui-style components,
  Playfair Display (headers) + Inter (body)

> The frontend uses the Tailwind Play CDN so the app runs with no build step.
> For production you can swap in a compiled Tailwind stylesheet.

## Run it locally
1. Install Python 3.10 or newer.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Start the app:
   ```bash
   python app.py
   ```
4. Open http://127.0.0.1:5000

Upload a picture (or drop your own `.jpg`/`.png` files in the project folder),
tune the options, preview, then click **Generate PDF puzzle** and print.

## Project structure
```
app.py              Flask routes (upload, preview, generate, download)
puzzle_maker.py    Piece/frame/template image generation (grid + jigsaw)
pdf_exporter.py    PDF assembly with selectable pages
templates/index.html  UI markup (Tailwind + shadcn-style structure)
static/
  style.css        Vintage Puzzle Studio theme + component styles
  components.js     cn() helper + dialog primitives (shadcn convention)
  script.js         App logic (gallery, preview, generate, dialogs)
wsgi.py             PythonAnywhere entry point (production only, git-ignored)
```

## Contributing
Pull requests are welcome. Keep the Vintage Puzzle Studio palette and the
shadcn/ui component conventions when changing the UI.

## License
[MIT](LICENSE)
