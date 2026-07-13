"""Smoke + regression tests for the Puzzly Flask app."""

import io

import app as app_module


# ---------------- Basic pages ----------------


def test_index_ok_with_security_headers(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["X-Frame-Options"] == "DENY"


def test_library_returns_json(client):
    resp = client.get("/library")
    assert resp.status_code == 200
    assert "images" in resp.get_json()


# ---------------- Upload validation ----------------


def test_upload_accepts_real_image(uploaded_file):
    assert uploaded_file.endswith(".png")


def test_upload_rejects_non_image(client):
    resp = client.post(
        "/upload",
        data={"images": (io.BytesIO(b"not an image"), "fake.png")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400
    assert "error" in resp.get_json()


# ---------------- Previews ----------------


def test_preview_missing_filename(client):
    assert client.post("/preview", json={}).status_code == 400


def test_preview_renders_for_uploaded_file(client, uploaded_file):
    resp = client.post("/preview", json={"filename": uploaded_file})
    assert resp.status_code == 200
    assert resp.get_json()["preview"].startswith("data:image/jpeg;base64,")


# ---------------- Generate ----------------


def test_generate_requires_at_least_one_page(client, uploaded_file):
    resp = client.post("/generate", json={"filename": uploaded_file, "pages": []})
    assert resp.status_code == 400
    assert "at least one page" in resp.get_json()["error"].lower()


def test_generate_missing_file(client):
    resp = client.post("/generate", json={"filename": "nope.png", "pages": ["framed"]})
    assert resp.status_code == 404


def test_generate_then_download(client, uploaded_file):
    resp = client.post(
        "/generate",
        json={"filename": uploaded_file, "rows": 3, "cols": 3, "pages": ["framed"]},
    )
    assert resp.status_code == 200
    url = resp.get_json()["download_url"]
    dl = client.get(url)
    assert dl.status_code == 200
    assert dl.data[:4] == b"%PDF"


# ---------------- Admin & CSRF ----------------


def test_admin_login_page_when_anonymous(client):
    resp = client.get("/admin")
    assert resp.status_code == 200
    assert b"Admin sign in" in resp.data


def test_admin_login_rejects_bad_token(client):
    assert client.post("/admin/login", data={"token": "wrong"}).status_code == 401


def test_admin_dashboard_renders(admin_client):
    resp = admin_client.get("/admin")
    assert resp.status_code == 200
    assert b"csrf-token" in resp.data


def test_admin_upload_blocked_without_csrf(admin_client, png_bytes):
    resp = admin_client.post(
        "/admin/library/upload",
        data={"images": (io.BytesIO(png_bytes), "x.png")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400
    assert "csrf" in resp.get_json()["error"].lower()


def test_admin_upload_succeeds_with_csrf(admin_client, png_bytes):
    resp = admin_client.post(
        "/admin/library/upload",
        data={"images": (io.BytesIO(png_bytes), "csrf_ok.png")},
        content_type="multipart/form-data",
        headers={"X-CSRF-Token": admin_client._csrf},
    )
    assert resp.status_code == 200
    uploaded = resp.get_json()["uploaded"]
    assert uploaded
    # Clean up the file we just added to the library.
    admin_client.post(
        "/admin/library/delete",
        json={"name": uploaded[0]},
        headers={"X-CSRF-Token": admin_client._csrf},
    )


# ---------------- Unit: clamp helper ----------------


def test_clamp_bounds_and_fallback():
    assert app_module._clamp("999", 2, 12, 4) == 12
    assert app_module._clamp("1", 2, 12, 4) == 2
    assert app_module._clamp("abc", 2, 12, 4) == 4
    assert app_module._clamp(None, 0, 20, 3) == 3
