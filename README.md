# Puzzly

> Turn any picture into a printable jigsaw or grid puzzle.

**Puzzly** is a small Flask web app that turns your photos into cut-and-play
puzzles for kids. Pick a picture, choose a style and size, preview live, and
export a print-ready PDF — scattered pieces, a one-page cut-in-place puzzle, a
reference sheet, and a framed placement template.

The interface uses a **Vintage Puzzle Studio** theme (warm cream, mahogany,
sage, gold) with **shadcn/ui-inspired** components styled with a locally
compiled Tailwind CSS build.

![license](https://img.shields.io/badge/license-MIT-blue.svg)

## Live demo
A hosted demo is live at **https://puzzly.pythonanywhere.com/** — try it
in your browser, or use it to turn your own pictures into printable puzzles.

## Features
- Upload your own images (JPG, PNG, WEBP, BMP, GIF) or pick from the built-in
  library of default pictures
- Two cut styles: simple **Grid** or interlocking **Jigsaw** pieces
- Adjustable piece count (rows × columns) with difficulty presets
- Customizable cut-line thickness, paper size (A4 / Letter / A3), and layout
- Live preview with a rounded physical puzzle-board frame
- Choose exactly which PDF pages to include (at least one is required):
  - **Framed puzzle board** — the picture with its frame and cut lines
  - **Cut-out pieces** — scattered to cut, or one printable page
  - **Reference sheet** — the solved picture
  - **Placement template** — a white board with piece outlines
- **Admin dashboard** (`/admin`) — usage stats, a per-day chart, recent
  activity, and management of the default picture library
- Uploaded and generated files are automatically deleted after a configurable
  TTL (default 1 hour)

## Tech stack
- **Backend:** Python 3.10+, Flask
- **Imaging:** Pillow (piece generation, framing, previews)
- **PDF:** fpdf2
- **Storage:** SQLite (usage logging only)
- **Frontend:** Vanilla JS + compiled Tailwind CSS, shadcn/ui-style components,
  Playfair Display (headers) + Inter (body)

## Run it locally
1. Install Python 3.10 or newer.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   For a reproducible production install, use `requirements.lock.txt`
   (fully pinned versions) instead.
3. Create a `.env` file (copy the example and fill it in):
   ```bash
   cp .env.example .env
   # then generate a key:
   python -c "import secrets; print(secrets.token_hex(32))"
   ```
   Put the value in `SECRET_KEY`. In debug mode a random key is generated
   automatically, but a fixed key is **required** when `FLASK_DEBUG` is off.
4. Start the app:
   ```bash
   python app.py
   ```
5. Open http://127.0.0.1:5000

## Configuration
All configuration is read from environment variables (via `.env`). See
[`.env.example`](.env.example) for the full list.

| Variable                | Default | Purpose |
| ----------------------- | ------- | ------- |
| `SECRET_KEY`            | —       | Flask session signing key. **Required in production**; auto-generated in debug. |
| `ADMIN_TOKEN`           | —       | Token to sign in at `/admin`. Leave empty to disable the admin page (returns 503). |
| `FLASK_DEBUG`           | `0`     | Set to `1` for auto-reload and a generated dev key. |
| `SESSION_COOKIE_SECURE` | `0`     | Set to `1` behind HTTPS so the session cookie is marked `Secure`. |
| `FILE_TTL_SECONDS`      | `3600`  | How long uploads/outputs live before deletion. |
| `PROXY_TRUSTED`         | `0`     | Set to `1` behind a proxy (e.g. PythonAnywhere) to record the real client IP. |
| `PORT`                  | `5000`  | Port for the built-in server. |

## The admin dashboard
Set `ADMIN_TOKEN` in your `.env`, then visit `/admin` and sign in with that
token. From there you can view usage stats and add/remove the default pictures
that appear in the picture library. Admin mutations are protected with a
per-session CSRF token.

## Rebuilding the Tailwind CSS
The compiled stylesheet at `static/tailwind.build.css` is committed, so the app
runs with no build step. If you change classes in the templates or JS, rebuild
it with the Tailwind CLI:

```bash
npx tailwindcss -i static/tailwind.input.css -o static/tailwind.build.css --minify
```

## Running the tests
```bash
pip install -r requirements-dev.txt
pytest
```

## Hosting
See [HOSTING.md](HOSTING.md) for deploying the demo (environment variables,
scheduled cleanup, and proxy/IP configuration).

## Project structure
```
app.py                 Flask routes, security, cleanup, CSRF, admin
puzzle_maker.py        Piece/frame/template image generation (grid + jigsaw)
pdf_exporter.py        PDF assembly with selectable pages
db.py                  SQLite usage logging
cleanup.py             TTL sweep of generated upload/output files
templates/
  index.html           Main UI
  admin.html           Admin dashboard
static/
  style.css            Vintage Puzzle Studio theme + component styles
  tailwind.input.css   Tailwind entry (source)
  tailwind.build.css   Compiled Tailwind output (committed)
  components.js        Dialog primitives (shadcn convention)
  script.js            App logic (gallery, preview, generate, dialogs)
  admin.js             Admin dashboard logic
tests/                 pytest smoke + regression suite
```

## Contributing
See [CONTRIBUTING.md](CONTRIBUTING.md). Pull requests are welcome — please keep
the Vintage Puzzle Studio palette and the shadcn/ui component conventions when
changing the UI.

## License
[MIT](LICENSE)
