"""Shared pytest fixtures.

Environment variables are set *before* importing the app module because
app.py reads configuration (SECRET_KEY, ADMIN_TOKEN, ...) at import time.
"""

import io
import os
import sys
from pathlib import Path

import pytest

# Add parent directory (project root) to sys.path so `import app` works
sys.path.insert(0, str(Path(__file__).parent.parent))

os.environ.setdefault("FLASK_DEBUG", "1")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("ADMIN_TOKEN", "test-admin-token")

from PIL import Image  # noqa: E402

import app as app_module  # noqa: E402

ADMIN_TOKEN = "test-admin-token"


@pytest.fixture()
def client():
    app_module.app.config.update(TESTING=True)
    return app_module.app.test_client()


@pytest.fixture()
def png_bytes():
    """A tiny valid PNG as raw bytes."""
    buf = io.BytesIO()
    Image.new("RGB", (64, 64), (200, 120, 60)).save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture()
def uploaded_file(client, png_bytes):
    """Upload a real image and return its stored filename."""
    resp = client.post(
        "/upload",
        data={"images": (io.BytesIO(png_bytes), "sample.png")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 200
    names = resp.get_json()["uploaded"]
    assert names
    return names[0]


@pytest.fixture()
def admin_client(client):
    """A client logged into /admin with a valid CSRF token available."""
    assert client.post("/admin/login", data={"token": ADMIN_TOKEN}).status_code == 302
    client.get("/admin")  # ensures a CSRF token is minted into the session
    with client.session_transaction() as sess:
        client._csrf = sess.get("csrf")
    return client
