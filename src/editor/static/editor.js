// Minimal editor. Loads layout JSON, renders elements as divs,
// wires up interact.js for drag/resize, handles inline text editing
// and roundtrip to the backend for PNG export.

let state = null;      // original EditorState (for reset)
let current = null;    // mutable working copy
let selectedEl = null;
let canvasScale = 1;

function $(id) { return document.getElementById(id); }
function toast(msg, ms = 2400) {
  const t = $("toast");
  t.textContent = msg;
  t.hidden = false;
  clearTimeout(toast._t);
  toast._t = setTimeout(() => { t.hidden = true; }, ms);
}

function deepCopy(o) { return JSON.parse(JSON.stringify(o)); }

// ---------- Load + render ----------

async function init() {
  const res = await fetch("/api/layout");
  if (!res.ok) { toast("Failed to load layout"); return; }
  state = await res.json();
  current = deepCopy(state);
  fitCanvas();
  renderCanvas();
  wireInteractions();
  wireUI();
  window.addEventListener("resize", () => { fitCanvas(); applyScale(); });
}

function fitCanvas() {
  const stage = $("stage");
  const availW = stage.clientWidth - 60;
  const availH = stage.clientHeight - 60;
  canvasScale = Math.min(availW / current.canvas_width, availH / current.canvas_height, 1);
  applyScale();
}

function applyScale() {
  const canvas = $("canvas");
  canvas.style.width = current.canvas_width + "px";
  canvas.style.height = current.canvas_height + "px";
  canvas.style.transform = `scale(${canvasScale})`;
  const wrapper = $("canvas-wrapper");
  wrapper.style.width = (current.canvas_width * canvasScale) + "px";
  wrapper.style.height = (current.canvas_height * canvasScale) + "px";
}

function renderCanvas() {
  const canvas = $("canvas");
  canvas.innerHTML = "";

  const backdrop = document.createElement("img");
  backdrop.id = "backdrop";
  backdrop.src = current.backdrop_url;
  canvas.appendChild(backdrop);

  // Product
  const prod = current.product;
  const productEl = document.createElement("div");
  productEl.className = "el product";
  productEl.dataset.kind = "product";
  productEl.dataset.id = "product";
  setBox(productEl, prod.x, prod.y, prod.width, prod.height);
  const img = document.createElement("img");
  img.src = prod.cutout_url;
  productEl.appendChild(img);
  canvas.appendChild(productEl);

  // Text elements
  current.texts.forEach(t => {
    const div = document.createElement("div");
    div.className = `el text ${t.font_role}`;
    div.dataset.kind = "text";
    div.dataset.id = t.id;
    div.textContent = t.content;
    setBox(div, t.x, t.y, t.width, "auto");
    div.style.fontSize = t.size + "px";
    div.style.color = t.color;
    div.style.textAlign = t.align;
    canvas.appendChild(div);
  });
}

function setBox(el, x, y, w, h) {
  el.style.left = x + "px";
  el.style.top = y + "px";
  if (w !== undefined && w !== "auto") el.style.width = w + "px";
  if (h !== undefined && h !== "auto") el.style.height = h + "px";
}

// ---------- Interactions ----------

function wireInteractions() {
  interact(".el")
    .draggable({
      allowFrom: ".el",
      inertia: false,
      modifiers: [interact.modifiers.restrictRect({ restriction: "parent" })],
      listeners: {
        start(event) { select(event.target); },
        move(event) {
          const t = event.target;
          const x = (parseFloat(t.style.left) || 0) + event.dx / canvasScale;
          const y = (parseFloat(t.style.top) || 0) + event.dy / canvasScale;
          t.style.left = x + "px";
          t.style.top = y + "px";
          syncFromDom(t);
          updateInspector();
        },
      },
    })
    .resizable({
      edges: { left: true, right: true, top: true, bottom: true },
      listeners: {
        start(event) { select(event.target); },
        move(event) {
          const t = event.target;
          const newW = event.rect.width / canvasScale;
          const newH = event.rect.height / canvasScale;
          t.style.width = newW + "px";
          t.style.height = newH + "px";
          const newX = (parseFloat(t.style.left) || 0) + event.deltaRect.left / canvasScale;
          const newY = (parseFloat(t.style.top) || 0) + event.deltaRect.top / canvasScale;
          t.style.left = newX + "px";
          t.style.top = newY + "px";

          // For text boxes: scale font size with height
          if (t.dataset.kind === "text") {
            const startSize = parseFloat(t.dataset.startSize || t.style.fontSize);
            const startHeight = parseFloat(t.dataset.startHeight || newH);
            if (!t.dataset.startSize) {
              t.dataset.startSize = startSize;
              t.dataset.startHeight = newH;
            }
            const ratio = newH / startHeight;
            t.style.fontSize = (startSize * ratio) + "px";
          }
          syncFromDom(t);
          updateInspector();
        },
        end(event) {
          const t = event.target;
          delete t.dataset.startSize;
          delete t.dataset.startHeight;
        },
      },
      modifiers: [
        interact.modifiers.restrictEdges({ outer: "parent" }),
        interact.modifiers.restrictSize({ min: { width: 20, height: 12 } }),
      ],
    })
    .on("tap", (event) => select(event.currentTarget))
    .on("doubletap", (event) => {
      const t = event.currentTarget;
      if (t.dataset.kind === "text") {
        t.contentEditable = "true";
        t.focus();
      }
    });

  // Blur editable text -> sync content
  document.addEventListener("blur", (e) => {
    const t = e.target;
    if (t.dataset && t.dataset.kind === "text" && t.contentEditable === "true") {
      t.contentEditable = "false";
      syncFromDom(t);
    }
  }, true);
}

function select(el) {
  if (selectedEl) selectedEl.classList.remove("selected");
  selectedEl = el;
  el.classList.add("selected");
  updateInspector();
}

function syncFromDom(el) {
  const id = el.dataset.id;
  const kind = el.dataset.kind;
  const x = Math.round(parseFloat(el.style.left) || 0);
  const y = Math.round(parseFloat(el.style.top) || 0);
  const w = Math.round(parseFloat(el.style.width) || 0);
  const h = Math.round(parseFloat(el.style.height) || 0);

  if (kind === "product") {
    current.product.x = x;
    current.product.y = y;
    current.product.width = w;
    current.product.height = h;
  } else if (kind === "text") {
    const t = current.texts.find(t => t.id === id);
    if (!t) return;
    t.x = x; t.y = y; t.width = w;
    const fs = Math.round(parseFloat(el.style.fontSize) || t.size);
    t.size = Math.max(8, fs);
    t.content = el.textContent;
  }
}

// ---------- Inspector ----------

function updateInspector() {
  const sel = $("selection");
  const none = $("no-selection");
  if (!selectedEl) { sel.hidden = true; none.hidden = false; return; }
  sel.hidden = false;
  none.hidden = true;

  const kind = selectedEl.dataset.kind;
  const id = selectedEl.dataset.id;
  $("sel-id").textContent = `${id} (${kind})`;

  $("sel-x").value = Math.round(parseFloat(selectedEl.style.left) || 0);
  $("sel-y").value = Math.round(parseFloat(selectedEl.style.top) || 0);
  $("sel-w").value = Math.round(parseFloat(selectedEl.style.width) || 0);
  $("sel-h").value = Math.round(parseFloat(selectedEl.style.height) || selectedEl.offsetHeight);

  const textOnly = document.querySelectorAll(".text-only");
  textOnly.forEach(el => el.style.display = kind === "text" ? "grid" : "none");

  if (kind === "text") {
    const t = current.texts.find(t => t.id === id);
    if (t) {
      $("sel-size").value = t.size;
      $("sel-align").value = t.align;
    }
  }
}

function wireUI() {
  for (const field of ["x", "y", "w", "h"]) {
    $("sel-" + field).addEventListener("input", (e) => {
      if (!selectedEl) return;
      const v = parseInt(e.target.value) || 0;
      if (field === "x") selectedEl.style.left = v + "px";
      if (field === "y") selectedEl.style.top = v + "px";
      if (field === "w") selectedEl.style.width = v + "px";
      if (field === "h") selectedEl.style.height = v + "px";
      syncFromDom(selectedEl);
    });
  }
  $("sel-size").addEventListener("input", (e) => {
    if (!selectedEl || selectedEl.dataset.kind !== "text") return;
    const v = parseInt(e.target.value) || 12;
    selectedEl.style.fontSize = v + "px";
    syncFromDom(selectedEl);
  });
  $("sel-align").addEventListener("change", (e) => {
    if (!selectedEl || selectedEl.dataset.kind !== "text") return;
    selectedEl.style.textAlign = e.target.value;
    const t = current.texts.find(t => t.id === selectedEl.dataset.id);
    if (t) t.align = e.target.value;
  });

  $("btn-reset").addEventListener("click", () => {
    current = deepCopy(state);
    renderCanvas();
    updateInspector();
    toast("Reset to defaults");
  });
  $("btn-export").addEventListener("click", exportPng);
}

async function exportPng() {
  toast("Rendering…");
  const payload = deepCopy(current);
  // Server doesn't need URLs
  delete payload.backdrop_url;
  delete payload.product.cutout_url;

  const res = await fetch("/api/render", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) { toast("Export failed"); return; }
  const data = await res.json();
  toast("Saved: " + data.output_path);
  // Open the rendered file in a new tab
  window.open(data.output_url, "_blank");
}

init();
