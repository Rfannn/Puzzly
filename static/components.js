/* ============================================================
   Puzzly UI primitives (shadcn/ui-inspired, vanilla JS)

   The shadcn/ui workflow relies on a `cn()` helper to merge
   conditional class names. We expose the same utility here so
   component classes can be composed predictably.
   ============================================================ */

// cn() - conditional className merge (clsx-style, no deps).
function cn(...inputs) {
    return inputs
        .flatMap((i) => {
            if (!i) return [];
            if (typeof i === "string") return [i];
            if (Array.isArray(i)) return i;
            if (typeof i === "object") {
                return Object.keys(i).filter((k) => i[k]);
            }
            return [];
        })
        .join(" ");
}

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
