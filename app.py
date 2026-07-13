"""Flask web app for Puzzly."""

import os
import uuid
import io
import base64
from flask import Flask, render_template, request, send_file, jsonify, url_for

import puzzle_maker
import pdf_exporter

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = os.path.join("static", "uploads")
app.config["OUTPUT_FOLDER"] = os.path.join("static", "output")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LIBRARY_DIR = BASE_DIR  # the 4 pictures live in the project folder

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
os.makedirs(app.config["OUTPUT_FOLDER"], exist_ok=True)

ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}


def library_images():
    """List image files present in the project folder (the provided pictures)."""
    if not os.path.isdir(LIBRARY_DIR):
        return []
    files = []
    for f in sorted(os.listdir(LIBRARY_DIR)):
        if os.path.splitext(f)[1].lower() in ALLOWED_EXTENSIONS and os.path.isfile(
            os.path.join(LIBRARY_DIR, f)
        ):
            files.append(f)
    return files


def allowed_file(filename):
    return os.path.splitext(filename)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload():
    files = request.files.getlist("images")
    saved = []
    for f in files:
        if f and allowed_file(f.filename):
            ext = os.path.splitext(f.filename)[1]
            name = f"{uuid.uuid4().hex}{ext}"
            path = os.path.join(app.config["UPLOAD_FOLDER"], name)
            f.save(path)
            saved.append(name)
    return jsonify({"uploaded": saved})


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
    import shutil

    shutil.copyfile(src, dst)
    return jsonify({"uploaded": new_name})


@app.route("/preview", methods=["POST"])
def preview():
    data = request.get_json(force=True) or {}
    filename = data.get("filename")
    puzzle_type = data.get("puzzle_type", "grid")
    rows = int(data.get("rows", 4))
    cols = int(data.get("cols", 4))
    border_width = int(data.get("border_width", 3))

    if not filename:
        return jsonify({"error": "No filename"}), 400

    path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    if not os.path.exists(path):
        return jsonify({"error": "File not found"}), 404

    preview_img = puzzle_maker.create_preview(
        path, rows, cols, puzzle_type, border_width
    )

    buf = io.BytesIO()
    preview_img.save(buf, format="JPEG", quality=85)
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode("utf-8")
    return jsonify({"preview": f"data:image/jpeg;base64,{b64}"})


@app.route("/preview-template", methods=["POST"])
def preview_template():
    data = request.get_json(force=True) or {}
    filename = data.get("filename")
    puzzle_type = data.get("puzzle_type", "grid")
    rows = int(data.get("rows", 4))
    cols = int(data.get("cols", 4))
    border_width = int(data.get("border_width", 3))

    if not filename:
        return jsonify({"error": "No filename"}), 400

    path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    if not os.path.exists(path):
        return jsonify({"error": "File not found"}), 404

    tpl_img = puzzle_maker.create_template_image(
        rows, cols, puzzle_type, 800, 600, border_width, path
    )
    buf = io.BytesIO()
    tpl_img.save(buf, format="JPEG", quality=85)
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode("utf-8")
    return jsonify({"preview": f"data:image/jpeg;base64,{b64}"})


@app.route("/preview-framed", methods=["POST"])
def preview_framed():
    data = request.get_json(force=True) or {}
    filename = data.get("filename")
    puzzle_type = data.get("puzzle_type", "grid")
    rows = int(data.get("rows", 4))
    cols = int(data.get("cols", 4))
    border_width = int(data.get("border_width", 3))

    if not filename:
        return jsonify({"error": "No filename"}), 400

    path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    if not os.path.exists(path):
        return jsonify({"error": "File not found"}), 404

    framed_img = puzzle_maker.create_framed_puzzle_image(
        path, rows, cols, puzzle_type, border_width
    )
    buf = io.BytesIO()
    framed_img.save(buf, format="JPEG", quality=85)
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode("utf-8")
    return jsonify({"preview": f"data:image/jpeg;base64,{b64}"})


@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json(force=True) or {}
    filename = data.get("filename")
    puzzle_type = data.get("puzzle_type", "grid")
    rows = int(data.get("rows", 4))
    cols = int(data.get("cols", 4))
    border_width = int(data.get("border_width", 3))
    paper_size = data.get("paper_size", "A4")
    difficulty = data.get("difficulty", "custom")
    output_size_mm = data.get("output_size_mm")
    layout = data.get("layout", "scattered")
    pages = data.get("pages", ["framed", "pieces", "reference", "template"])

    if not filename:
        return jsonify({"error": "No filename"}), 400

    path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    if not os.path.exists(path):
        return jsonify({"error": "File not found"}), 404

    out_name = f"puzzle_{uuid.uuid4().hex[:8]}.pdf"
    out_path = os.path.join(app.config["OUTPUT_FOLDER"], out_name)

    pdf_exporter.generate_pdf(
        image_path=path,
        output_path=out_path,
        rows=rows,
        cols=cols,
        puzzle_type=puzzle_type,
        border_width=border_width,
        paper_size=paper_size,
        output_size_mm=output_size_mm,
        difficulty=difficulty,
        layout=layout,
        pages=pages,
    )

    return jsonify({"download_url": url_for("download", filename=out_name)})


@app.route("/download/<filename>")
def download(filename):
    path = os.path.join(app.config["OUTPUT_FOLDER"], filename)
    if not os.path.exists(path):
        return "File not found", 404
    return send_file(path, as_attachment=True, download_name="puzzle.pdf")


app.secret_key = os.environ.get("SECRET_KEY", "puzzly-dev-secret-key")

if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=debug, host="0.0.0.0", port=port)
