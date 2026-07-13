"use strict";

const $ = (id) => document.getElementById(id);

function csrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute("content") : "";
}

function adminStatus(kind, msg) {
    const el = $("adminStatus");
    if (!el) return;
    el.hidden = false;
    el.className = "status " + kind;
    el.textContent = msg;
}

async function loadAdminLibrary() {
    const gal = $("adminGallery");
    try {
        const res = await fetch("/library");
        const data = await res.json();
        renderAdminGallery(data.images || []);
    } catch (e) {
        gal.innerHTML = '<div class="gallery-empty">Could not load pictures.</div>';
    }
}

function renderAdminGallery(names) {
    const gal = $("adminGallery");
    if (!names.length) {
        gal.innerHTML = '<div class="gallery-empty">No default pictures yet.</div>';
        return;
    }
    gal.innerHTML = "";
    names.forEach((name) => {
        const div = document.createElement("div");
        div.className = "thumb admin-thumb";
        div.innerHTML = `
            <img src="/library/${encodeURIComponent(name)}" alt="${name}">
            <button class="thumb-del" title="Delete" aria-label="Delete ${name}">&times;</button>`;
        div.querySelector(".thumb-del").addEventListener("click", () =>
            deleteImage(name)
        );
        gal.appendChild(div);
    });
}

async function deleteImage(name) {
    if (!confirm(`Delete "${name}" from default pictures?`)) return;
    try {
        const res = await fetch("/admin/library/delete", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRF-Token": csrfToken(),
            },
            body: JSON.stringify({ name }),
        });
        const data = await res.json();
        if (data.deleted) {
            adminStatus("success", `Deleted ${data.deleted}`);
            loadAdminLibrary();
        } else {
            adminStatus("error", data.error || "Delete failed");
        }
    } catch (e) {
        adminStatus("error", "Delete failed");
    }
}

function handleAdminUpload(files) {
    const fd = new FormData();
    for (const f of files) fd.append("images", f);
    adminStatus("loading", "Uploading...");
    fetch("/admin/library/upload", {
        method: "POST",
        headers: { "X-CSRF-Token": csrfToken() },
        body: fd,
    })
        .then((r) => r.json())
        .then((data) => {
            if (data.uploaded && data.uploaded.length) {
                adminStatus("success", `Added ${data.uploaded.length} picture(s)`);
                loadAdminLibrary();
            } else {
                adminStatus("error", data.error || "Upload failed");
            }
        })
        .catch(() => adminStatus("error", "Upload failed"));
}

$("adminFileInput").addEventListener("change", (e) =>
    handleAdminUpload(e.target.files)
);

loadAdminLibrary();
