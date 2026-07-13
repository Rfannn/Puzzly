"use strict";

const state = {
    currentFile: null,
    sourceName: null,
    previewTimer: null,
    generating: false,
};

const $ = (id) => document.getElementById(id);

/* ---------------- Segmented controls ---------------- */
function initSegmented(id) {
    const group = $(id);
    group.querySelectorAll("button").forEach((btn) => {
        btn.addEventListener("click", () => {
            group.querySelectorAll("button").forEach((b) => b.classList.remove("active"));
            btn.classList.add("active");
            group.dataset.value = btn.dataset.value;
            requestPreview();
        });
    });
    // set initial active
    const initial = group.querySelector(`button[data-value="${group.dataset.value}"]`);
    if (initial) initial.classList.add("active");
}

/* ---------------- Image gallery ---------------- */
async function loadLibrary() {
    try {
        const res = await fetch("/library");
        const data = await res.json();
        renderGallery(data.images || []);
    } catch (e) {
        $("gallery").innerHTML = '<div class="gallery-empty">Could not load pictures.</div>';
    }
}

function renderGallery(names) {
    const gal = $("gallery");
    if (!names.length) {
        gal.innerHTML = '<div class="gallery-empty">No pictures found in the folder.</div>';
        return;
    }
    gal.innerHTML = "";
    names.forEach((name) => {
        const div = document.createElement("div");
        div.className = "thumb";
        div.dataset.name = name;
        div.innerHTML = `
            <img src="/library/${encodeURIComponent(name)}" alt="${name}">
            <span class="check">✓</span>`;
        div.addEventListener("click", () => selectLibraryImage(name, div));
        gal.appendChild(div);
    });
}

async function selectLibraryImage(name, el) {
    setSelectedThumb(el);
    $("previewHint").textContent = "Importing...";
    try {
        const res = await fetch("/import", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name }),
        });
        const data = await res.json();
        if (data.uploaded) {
            state.currentFile = data.uploaded;
            state.sourceName = data.source || name;
            requestPreview();
        }
    } catch (e) {
        $("previewHint").textContent = "Import failed";
    }
}

function setSelectedThumb(el) {
    document.querySelectorAll(".thumb").forEach((t) => t.classList.remove("selected"));
    if (el) el.classList.add("selected");
}

/* ---------------- Upload ---------------- */
function handleFiles(files) {
    const fd = new FormData();
    for (const f of files) fd.append("images", f);
    $("previewHint").textContent = "Uploading...";
    fetch("/upload", { method: "POST", body: fd })
        .then((r) => r.json())
        .then((data) => {
            if (data.uploaded && data.uploaded.length) {
                const name = data.uploaded[0];
                state.currentFile = name;
                state.sourceName = "upload";
                addUploadedThumb(name);
                requestPreview();
            }
        })
        .catch(() => ($("previewHint").textContent = "Upload failed"));
}

function addUploadedThumb(name) {
    const gal = $("gallery");
    const div = document.createElement("div");
    div.className = "thumb selected";
    div.innerHTML = `
        <img src="/static/uploads/${name}" alt="uploaded">
        <span class="check">✓</span>`;
    div.addEventListener("click", () => {
        state.currentFile = name;
        state.sourceName = "upload";
        setSelectedThumb(div);
        requestPreview();
    });
    setSelectedThumb(div);
    gal.prepend(div);
}

$("fileInput").addEventListener("change", (e) => handleFiles(e.target.files));

/* drag & drop anywhere on the upload area */
const uploadArea = $("uploadBtn");
["dragover", "dragenter"].forEach((ev) =>
    uploadArea.addEventListener(ev, (e) => {
        e.preventDefault();
        uploadArea.style.borderColor = "var(--mahogany)";
    })
);
["dragleave", "drop"].forEach((ev) =>
    uploadArea.addEventListener(ev, (e) => {
        e.preventDefault();
        uploadArea.style.borderColor = "";
    })
);
uploadArea.addEventListener("drop", (e) => {
    if (e.dataTransfer.files.length) handleFiles(e.dataTransfer.files);
});

/* ---------------- Options wiring ---------------- */
initSegmented("puzzleType");
initSegmented("layout");
initSegmented("borderWidth");

const difficultySelect = $("difficulty");
difficultySelect.addEventListener("change", () => {
    const v = difficultySelect.value;
    if (v === "easy") { setRowsCols(2, 2); }
    else if (v === "medium") { setRowsCols(3, 3); }
    else if (v === "hard") { setRowsCols(4, 4); }
    else if (v === "expert") { setRowsCols(5, 5); }
    else if (v === "wide") { setRowsCols(4, 5); }
    requestPreview();
});

function setRowsCols(r, c) {
    $("rows").value = r;
    $("cols").value = c;
}

["rows", "cols", "paperSize"].forEach((id) => {
    $(id).addEventListener("change", () => {
        if (id === "rows" || id === "cols") difficultySelect.value = "custom";
        requestPreview();
    });
});

document.querySelectorAll(".page-opt").forEach((el) =>
    el.addEventListener("change", () => {
        updateGenerateState();
        requestPreview();
    })
);

function anyPageSelected() {
    return document.querySelectorAll(".page-opt:checked").length > 0;
}

function updateGenerateState() {
    const btn = $("generateBtn");
    if (!state.currentFile) return;
    const ok = anyPageSelected();
    btn.disabled = !ok || state.generating;
    const hint = $("pagesHint");
    if (hint) hint.hidden = ok;
}

/* ---------------- Live preview ---------------- */
function getOptions() {
    return {
        filename: state.currentFile,
        source_name: state.sourceName,
        puzzle_type: $("puzzleType").dataset.value,
        layout: $("layout").dataset.value,
        rows: parseInt($("rows").value, 10) || 3,
        cols: parseInt($("cols").value, 10) || 3,
        border_width: parseInt($("borderWidth").dataset.value, 10) || 3,
        paper_size: $("paperSize").value,
        pages: Array.from(document.querySelectorAll(".page-opt:checked")).map(
            (el) => el.value
        ),
    };
}

function requestPreview() {
    if (!state.currentFile) return;
    updateGenerateState();
    $("previewHint").textContent = "Updating preview...";
    clearTimeout(state.previewTimer);
    state.previewTimer = setTimeout(doPreview, 220);
}

async function doPreview() {
    const opts = getOptions();
    // Preview priority: framed board (first page) -> blank template -> plain.
    let url = "/preview";
    let hint = "Updates as you change options";
    if (opts.pages.includes("framed")) {
        url = "/preview-framed";
        hint = "Framed puzzle board - picture with frame & cut lines";
    } else if (opts.pages.includes("template")) {
        url = "/preview-template";
        hint = "Template preview - white board with piece outlines";
    }
    try {
        const res = await fetch(url, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(opts),
        });
        const data = await res.json();
        if (data.preview) {
            $("previewWrap").innerHTML = `<img src="${data.preview}" alt="Preview">`;
            $("previewHint").textContent = hint;
        } else {
            throw new Error(data.error || "no preview");
        }
    } catch (e) {
        $("previewHint").textContent = "Preview failed";
    }
}

/* ---------------- Generate ---------------- */
$("generateBtn").addEventListener("click", async () => {
    if (!state.currentFile || state.generating) return;
    if (!anyPageSelected()) {
        showStatus("error", "Select at least one page to include in the PDF.");
        updateGenerateState();
        return;
    }
    state.generating = true;
    const btn = $("generateBtn");
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Generating...';
    showStatus("loading", "Building your PDF puzzle...");

    const opts = getOptions();
    try {
        const res = await fetch("/generate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(opts),
        });
        const data = await res.json();
        if (data.download_url) {
            showStatus(
                "success",
                `Ready! <a href="${data.download_url}" target="_blank" rel="noopener">Open / download PDF</a>`
            );
        } else {
            throw new Error(data.error || "generation failed");
        }
    } catch (e) {
        showStatus("error", e.message || "Could not generate the puzzle. Please try again.");
    } finally {
        state.generating = false;
        btn.disabled = false;
        btn.innerHTML = `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3"/></svg> Generate PDF puzzle`;
    }
});

function showStatus(kind, html) {
    const el = $("status");
    el.hidden = false;
    el.className = "status " + kind;
    el.innerHTML = html;
}

/* ---------------- Dialogs ---------------- */
function setupDialogs() {
    document.querySelectorAll(".dialog-overlay").forEach((overlay) => {
        overlay.addEventListener("click", (e) => {
            if (e.target === overlay || e.target.closest("[data-close]")) {
                closeDialog(overlay);
            }
        });
    });
    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape") {
            const open = document.querySelector(".dialog-overlay:not([hidden])");
            if (open) closeDialog(open);
        }
    });
    const tips = $("tipsBtn");
    if (tips) tips.addEventListener("click", () => openDialog("tipsDialog"));
    $("previewWrap").addEventListener("click", (e) => {
        const img = e.target.closest("img");
        if (img) openDialog("previewDialog", img.outerHTML);
    });
}

/* ---------------- Init ---------------- */
setupDialogs();
loadLibrary();
