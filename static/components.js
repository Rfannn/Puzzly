/* ============================================================
   Puzzly UI primitives (shadcn/ui-inspired, vanilla JS)
   ============================================================ */

// Open a dialog overlay by id. Optionally inject body HTML (preview lightbox).
function openDialog(id, bodyHtml) {
    const d = document.getElementById(id);
    if (!d) return;
    if (bodyHtml && id === "previewDialog") {
        document.getElementById("previewDialogBody").innerHTML = bodyHtml;
    }
    d.hidden = false;
    document.body.style.overflow = "hidden";
    const focusTarget = d.querySelector("[data-close], .dialog-close");
    if (focusTarget) focusTarget.focus();
}

// Close a dialog overlay.
function closeDialog(d) {
    if (!d) return;
    d.hidden = true;
    document.body.style.overflow = "";
}
