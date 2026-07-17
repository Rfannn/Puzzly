"""Flask web app for Puzzly."""

import os
import io
import json
import uuid
import time
import hmac
import base64
import shutil
import secrets
import threading
from functools import wraps

from dotenv import load_dotenv
from PIL import Image, UnidentifiedImageError
from werkzeug.utils import secure_filename
from flask import (
    Flask,
    render_template,
    request,
    send_file,
    jsonify,
    url_for,
    session,
    redirect,
    abort,
)

import puzzle_maker
import pdf_exporter
import db
import cleanup
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

load_dotenv()

DEBUG = os.environ.get("FLASK_DEBUG", "0") == "1"

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = os.path.join("static", "uploads")
app.config["OUTPUT_FOLDER"] = os.path.join("static", "output")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB

# ---- Session signing key (required in production) ----
_secret = os.environ.get("SECRET_KEY")
if not _secret:
    if DEBUG:
        _secret = secrets.token_hex(32)
        print(
            "WARNING: SECRET_KEY not set - using a random dev key. "
            "Sessions reset on restart. Set SECRET_KEY in .env."
        )
    else:
        raise RuntimeError(
            "SECRET_KEY is not set. Create a .env with SECRET_KEY=<random hex> "
            "(python -c \"import secrets; print(secrets.token_hex(32))\")."
        )
app.secret_key = _secret

# ---- Secure cookie defaults ----
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE", "0") == "1",
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LIBRARY_DIR = os.path.join(BASE_DIR, "library")  # managed default pictures

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
os.makedirs(app.config["OUTPUT_FOLDER"], exist_ok=True)
os.makedirs(LIBRARY_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}
# Trust X-Forwarded-For for the client IP only when behind a known proxy
# (e.g. PythonAnywhere).
PROXY_TRUSTED = os.environ.get("PROXY_TRUSTED", "0") == "1"

# ---- Rate limiting (public, unauthenticated, CPU-heavy endpoints) ----
def _rate_limit_key():
    return client_ip() or get_remote_address()


limiter = Limiter(
    key_func=_rate_limit_key,
    app=app,
    storage_uri="memory://",
    default_limits=["200 per hour"],
    headers_enabled=True,
)

ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN")

# ---- Background + opportunistic file cleanup (1-hour TTL) ----
FILE_TTL = int(os.environ.get("FILE_TTL_SECONDS", "3600"))
_last_sweep = 0.0
_sweep_lock = threading.Lock()


def _sweep_files():
    try:
        cleanup.sweep(max_age=FILE_TTL)
    except Exception:
        pass


def _cleanup_thread():
    while True:
        time.sleep(min(FILE_TTL, 600))
        _sweep_files()


threading.Thread(target=_cleanup_thread, daemon=True).start()


@app.before_request
def _opportunistic_cleanup():
    """Throttled sweep so cleanup also runs on hosts without a live thread."""
    global _last_sweep
    now = time.time()
    if now - _last_sweep > 60:
        with _sweep_lock:
            if now - _last_sweep > 60:
                _last_sweep = now
                _sweep_files()


@app.after_request
def _security_headers(resp):
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("X-Frame-Options", "DENY")
    resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    return resp


def _clamp(value, low, high, default):
    """Coerce `value` to an int within [low, high], falling back to default."""
    try:
        return max(low, min(high, int(value)))
    except (TypeError, ValueError):
        return default


def _resize_if_large(path, max_dim=2000):
    """Downscale image at `path` in-place if either dimension exceeds `max_dim`.
    Returns the path unchanged for small images. Uses Pillow (already a dep)."""
    try:
        with Image.open(path) as im:
            w, h = im.size
            if w <= max_dim and h <= max_dim:
                return
            scale = max_dim / max(w, h)
            new_w, new_h = max(1, int(w * scale)), max(1, int(h * scale))
            im = im.convert("RGB")
            im = im.resize((new_w, new_h), Image.LANCZOS)
            im.save(path, quality=85)
    except Exception:
        pass  # leave original file if anything goes wrong


ROWS_MIN, ROWS_MAX = 2, 12
BORDER_MIN, BORDER_MAX = 0, 20


def client_ip():
    """Best-effort client IP, honoring a proxy's X-Forwarded-For first hop
    only when running behind a trusted proxy (PROXY_TRUSTED=1)."""
    if PROXY_TRUSTED:
        fwd = request.headers.get("X-Forwarded-For")
        if fwd:
            return fwd.split(",")[0].strip()
    return request.remote_addr


def is_valid_image(path):
    """True if the file at `path` is a real, decodable image."""
    try:
        with Image.open(path) as im:
            im.verify()
        return True
    except (UnidentifiedImageError, OSError, ValueError):
        return False


def require_admin(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not ADMIN_TOKEN:
            abort(503)
        if not session.get("is_admin"):
            if request.method != "GET":
                return jsonify({"error": "Unauthorized"}), 401
            return redirect(url_for("admin"))
        if request.method == "POST" and not _csrf_ok():
            return jsonify({"error": "Invalid CSRF token"}), 400
        return fn(*args, **kwargs)

    return wrapper


def _csrf_token():
    """Return the session CSRF token, creating one if needed."""
    token = session.get("csrf")
    if not token:
        token = secrets.token_urlsafe(32)
        session["csrf"] = token
    return token


def _csrf_ok():
    sent = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token")
    expected = session.get("csrf")
    return bool(expected) and bool(sent) and hmac.compare_digest(sent, expected)


def library_images():
    """List image files present in the project folder (the default pictures)."""
    if not os.path.isdir(LIBRARY_DIR):
        return []
    files = []
    for f in sorted(os.listdir(LIBRARY_DIR)):
        if ".thumb" in f:
            continue
        if os.path.splitext(f)[1].lower() in ALLOWED_EXTENSIONS and os.path.isfile(
            os.path.join(LIBRARY_DIR, f)
        ):
            files.append(f)
    return files


def allowed_file(filename):
    return os.path.splitext(filename)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/")
def index():
    # Views are not logged per-hit to avoid a write on every landing page
    # load; only meaningful actions (generations) are recorded.
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
@limiter.limit("30 per minute")
def upload():
    files = request.files.getlist("images")
    saved = []
    rejected = []
    for f in files:
        if not f or not allowed_file(f.filename):
            if f and f.filename:
                rejected.append(f.filename)
            continue
        ext = os.path.splitext(f.filename)[1]
        name = f"{uuid.uuid4().hex}{ext}"
        path = os.path.join(app.config["UPLOAD_FOLDER"], name)
        f.save(path)
        _resize_if_large(path)
        if is_valid_image(path):
            saved.append(name)
        else:
            try:
                os.remove(path)
            except OSError:
                pass
            rejected.append(f.filename)
    if not saved and rejected:
        return jsonify({"error": "Those files are not valid images."}), 400
    return jsonify({"uploaded": saved, "rejected": rejected})


@app.route("/library")
def library():
    """List the pictures available in the project folder."""
    return jsonify({"images": library_images()})


@app.route("/library/<path:name>")
def library_file(name):
    """Serve a picture from the project folder (for gallery thumbnails)."""
    safe = os.path.basename(name)
    path = os.path.join(LIBRARY_DIR, safe)
    if not os.path.exists(path) or safe not in library_images():
        return "Not found", 404
    return send_file(path)


@app.route("/import", methods=["POST"])
def import_library_image():
    """Copy a picture from the project folder into uploads for processing."""
    data = request.get_json(force=True) or {}
    name = data.get("name")
    if not name:
        return jsonify({"error": "No name"}), 400
    safe = os.path.basename(name)
    src = os.path.join(LIBRARY_DIR, safe)
    if not os.path.exists(src) or safe not in library_images():
        return jsonify({"error": "Not found"}), 404
    ext = os.path.splitext(safe)[1]
    new_name = f"{uuid.uuid4().hex}{ext}"
    dst = os.path.join(app.config["UPLOAD_FOLDER"], new_name)
    shutil.copyfile(src, dst)
    return jsonify({"uploaded": new_name, "source": safe})


# ---- Preview rendering with a small in-memory cache ----
_PREVIEW_CACHE = {}
_PREVIEW_CACHE_MAX = 48


def _render_preview(kind, path, rows, cols, puzzle_type, border_width, tab_style="classic", watermark=False, watermark_text=""):
    """Return a JPEG data-URL for the requested preview, cached by inputs.

    Previews are rendered from a downscaled thumbnail so a large source image
    does not trigger expensive work on every option change."""
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        mtime = 0
    key = (kind, path, mtime, rows, cols, puzzle_type, border_width, tab_style, watermark, watermark_text)
    cached = _PREVIEW_CACHE.get(key)
    if cached:
        return cached

    preview_path = puzzle_maker.preview_thumbnail(path, size=800)

    if kind == "framed":
        img = puzzle_maker.create_framed_puzzle_image(
            preview_path, rows, cols, puzzle_type, border_width, tab_style=tab_style
        )
    elif kind == "template":
        img = puzzle_maker.create_template_image(
            rows, cols, puzzle_type, 800, 600, border_width, preview_path, tab_style=tab_style
        )
    else:
        img = puzzle_maker.create_preview(
            preview_path, rows, cols, puzzle_type, border_width, tab_style=tab_style
        )

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    data_url = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()

    if len(_PREVIEW_CACHE) >= _PREVIEW_CACHE_MAX:
        _PREVIEW_CACHE.pop(next(iter(_PREVIEW_CACHE)))
    return data_url


def _preview_response(kind):
    data = request.get_json(force=True) or {}
    filename = data.get("filename")
    if not filename:
        return jsonify({"error": "No filename"}), 400
    path = os.path.join(app.config["UPLOAD_FOLDER"], os.path.basename(filename))
    if not os.path.exists(path):
        return jsonify({"error": "File not found"}), 404
    try:
        data_url = _render_preview(
            kind,
            path,
            _clamp(data.get("rows"), ROWS_MIN, ROWS_MAX, 4),
            _clamp(data.get("cols"), ROWS_MIN, ROWS_MAX, 4),
            data.get("puzzle_type", "grid"),
            _clamp(data.get("border_width"), BORDER_MIN, BORDER_MAX, 3),
            data.get("tab_style", "classic"),
            data.get("watermark", False),
            data.get("watermark_text", ""),
        )
    except Exception as e:
        return jsonify({"error": f"Preview failed: {e}"}), 500
    return jsonify({"preview": data_url})


@app.route("/transform", methods=["POST"])
def transform_image():
    data = request.get_json(force=True) or {}
    filename = data.get("filename")
    rotate_deg = _clamp(data.get("rotate_deg"), -270, 270, 0)
    flip_h = data.get("flip_h", False)
    if not filename:
        return jsonify({"error": "No filename"}), 400
    path = os.path.join(app.config["UPLOAD_FOLDER"], os.path.basename(filename))
    if not os.path.exists(path):
        return jsonify({"error": "File not found"}), 404
    try:
        with Image.open(path) as im:
            if rotate_deg:
                im = im.rotate(-rotate_deg, expand=True)
            if flip_h:
                im = im.transpose(Image.FLIP_LEFT_RIGHT)
            ext = os.path.splitext(path)[1]
            new_name = f"{uuid.uuid4().hex}{ext}"
            new_path = os.path.join(app.config["UPLOAD_FOLDER"], new_name)
            im.save(new_path)
        return jsonify({"filename": new_name})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/preview", methods=["POST"])
def preview():
    return _preview_response("plain")


@app.route("/preview-template", methods=["POST"])
def preview_template():
    return _preview_response("template")


@app.route("/preview-framed", methods=["POST"])
def preview_framed():
    return _preview_response("framed")


@app.route("/generate", methods=["POST"])
@limiter.limit("20 per minute")
def generate():
    data = request.get_json(force=True) or {}
    filename = data.get("filename")
    puzzle_type = data.get("puzzle_type", "grid")
    tab_style = data.get("tab_style", "classic")
    rows = _clamp(data.get("rows"), ROWS_MIN, ROWS_MAX, 4)
    cols = _clamp(data.get("cols"), ROWS_MIN, ROWS_MAX, 4)
    border_width = _clamp(data.get("border_width"), BORDER_MIN, BORDER_MAX, 3)
    paper_size = data.get("paper_size", "A4")
    layout = data.get("layout", "scattered")
    valid_pages = ["framed", "pieces", "reference", "template"]
    pages = [p for p in (data.get("pages") or []) if p in valid_pages]
    source_name = data.get("source_name") or "upload"

    if not filename:
        return jsonify({"error": "No filename"}), 400

    if not pages:
        return jsonify({"error": "Select at least one page to include."}), 400

    path = os.path.join(app.config["UPLOAD_FOLDER"], os.path.basename(filename))
    if not os.path.exists(path):
        return jsonify({"error": "File not found"}), 404

    out_name = f"puzzle_{uuid.uuid4().hex[:8]}.pdf"
    out_path = os.path.join(app.config["OUTPUT_FOLDER"], out_name)

    try:
        pdf_exporter.generate_pdf(
            image_path=path,
            output_path=out_path,
            rows=rows,
            cols=cols,
            puzzle_type=puzzle_type,
            border_width=border_width,
            paper_size=paper_size,
            layout=layout,
            pages=pages,
            tab_style=tab_style,
            watermark=data.get("watermark", False),
            watermark_text=data.get("watermark_text", ""),
        )
    except Exception as e:
        return jsonify({"error": f"Could not build the PDF: {e}"}), 500

    db.log_event(
        "generate",
        picture=source_name,
        options={
            "puzzle_type": puzzle_type,
            "tab_style": tab_style,
            "watermark": data.get("watermark", False),
            "watermark_text": data.get("watermark_text", ""),
            "rows": rows,
            "cols": cols,
            "border_width": border_width,
            "paper_size": paper_size,
            "layout": layout,
            "pages": pages,
        },
        ip=client_ip(),
        user_agent=request.headers.get("User-Agent"),
    )

    return jsonify({"download_url": url_for("download", filename=out_name)})


@app.route("/download/<filename>")
def download(filename):
    path = os.path.join(app.config["OUTPUT_FOLDER"], os.path.basename(filename))
    if not os.path.exists(path):
        return "File not found", 404
    return send_file(path, as_attachment=True, download_name="puzzle.pdf")


# ---------------- Admin ----------------


@app.route("/admin")
def admin():
    if not ADMIN_TOKEN:
        abort(503)
    if not session.get("is_admin"):
        return render_template("admin.html", authed=False)
    recent = db.recent_events(100)
    for e in recent:
        e["options_summary"] = _summarize_options(e.get("options"))
    by_day = db.generations_by_day(30)
    stats = {
        "totals": db.total_by_kind(),
        "generations_30d": db.count_generations_since(30),
        "top_pictures": db.top_pictures(10),
        "by_day": by_day,
        "by_day_max": max((d["count"] for d in by_day), default=0),
        "recent": recent,
    }
    return render_template(
        "admin.html", authed=True, stats=stats, csrf_token=_csrf_token()
    )


def _summarize_options(options_json):
    """Turn a stored options JSON blob into a short human string."""
    if not options_json:
        return ""
    try:
        o = json.loads(options_json)
    except (ValueError, TypeError):
        return options_json
    parts = []
    if o.get("puzzle_type"):
        parts.append(o["puzzle_type"])
    if o.get("rows") and o.get("cols"):
        parts.append(f"{o['rows']}x{o['cols']}")
    if o.get("paper_size"):
        parts.append(o["paper_size"])
    if o.get("pages"):
        parts.append("+".join(o["pages"]))
    return " · ".join(parts)


@app.route("/admin/login", methods=["POST"])
@limiter.limit("5 per minute")
def admin_login():
    if not ADMIN_TOKEN:
        abort(503)
    token = (request.form.get("token") or "").strip()
    if token and hmac.compare_digest(token, ADMIN_TOKEN):
        session["is_admin"] = True
        return redirect(url_for("admin"))
    time.sleep(1)  # blunt brute-forcing
    return render_template("admin.html", authed=False, error="Invalid token"), 401


@app.route("/admin/logout", methods=["POST"])
def admin_logout():
    session.pop("is_admin", None)
    return redirect(url_for("admin"))


@app.route("/admin/library/upload", methods=["POST"])
@require_admin
def admin_library_upload():
    files = request.files.getlist("images")
    saved = []
    for f in files:
        if f and allowed_file(f.filename):
            name = secure_filename(f.filename)
            if not name:
                continue
            dst = os.path.join(LIBRARY_DIR, name)
            base, ext = os.path.splitext(name)
            i = 1
            while os.path.exists(dst):
                name = f"{base}_{i}{ext}"
                dst = os.path.join(LIBRARY_DIR, name)
                i += 1
            f.save(dst)
            if is_valid_image(dst):
                saved.append(name)
            else:
                try:
                    os.remove(dst)
                except OSError:
                    pass
    if not saved:
        return jsonify({"error": "No valid images uploaded."}), 400
    return jsonify({"uploaded": saved})


@app.route("/admin/library/delete", methods=["POST"])
@require_admin
def admin_library_delete():
    data = request.get_json(force=True) or {}
    name = data.get("name")
    if not name:
        return jsonify({"error": "No name"}), 400
    safe = os.path.basename(name)
    if safe not in library_images():
        return jsonify({"error": "Not found"}), 404
    try:
        os.remove(os.path.join(LIBRARY_DIR, safe))
    except OSError:
        return jsonify({"error": "Could not delete"}), 500
    return jsonify({"deleted": safe})


@app.errorhandler(413)
def too_large(_e):
    limit = app.config.get("MAX_CONTENT_LENGTH", 0)
    mb = round(limit / (1024 * 1024), 1) if limit else None
    msg = f"File too large. Max upload size is {mb} MB." if mb else "File too large."
    return jsonify({"error": msg}), 413


@app.errorhandler(429)
def rate_limited(_e):
    return jsonify({"error": "Too many requests. Please slow down and try again."}), 429


@app.errorhandler(404)
def not_found(_e):
    if request.path.startswith("/api") or request.is_json:
        return jsonify({"error": "Not found"}), 404
    return render_template("index.html"), 404


if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=debug, host="0.0.0.0", port=port)
