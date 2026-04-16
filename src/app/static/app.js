// MM Statics Builder — frontend logic
let config = null;
let currentRunId = null;
let pollTimer = null;
let renderedVariants = new Set();
let refFile = null;
let committedRatings = {};  // card index → committed rating value

// ---------- Init ----------

document.addEventListener("DOMContentLoaded", async () => {
  const res = await fetch("/api/config");
  config = await res.json();
  populateForm();
  wireEvents();
});

function populateForm() {
  // Ingredients checkboxes
  const list = document.getElementById("ingredients-list");
  config.ingredients.forEach(ing => {
    const label = document.createElement("label");
    label.innerHTML = `<input type="checkbox" value="${ing.keyword}" /> ${ing.display_name}`;
    list.appendChild(label);
  });

  // Format radios
  const radios = document.getElementById("format-radios");
  config.formats.forEach((fmt, i) => {
    const label = document.createElement("label");
    label.innerHTML = `<input type="radio" name="format" value="${fmt}" ${i === 1 ? "checked" : ""} /> ${fmt}`;
    radios.appendChild(label);
  });

  // Template select
  const sel = document.getElementById("template-select");
  for (const [key, val] of Object.entries(config.templates)) {
    const opt = document.createElement("option");
    opt.value = key;
    opt.textContent = `${key} — ${val}`;
    sel.appendChild(opt);
  }
}

// ---------- Events ----------

function wireEvents() {
  document.getElementById("form").addEventListener("submit", onGenerate);

  // Dropzone
  const dz = document.getElementById("dropzone");
  const fileInput = document.getElementById("ref-input");
  dz.addEventListener("click", () => fileInput.click());
  dz.addEventListener("dragover", e => { e.preventDefault(); dz.classList.add("dragover"); });
  dz.addEventListener("dragleave", () => dz.classList.remove("dragover"));
  dz.addEventListener("drop", e => {
    e.preventDefault(); dz.classList.remove("dragover");
    if (e.dataTransfer.files.length) setRefFile(e.dataTransfer.files[0]);
  });
  fileInput.addEventListener("change", () => { if (fileInput.files.length) setRefFile(fileInput.files[0]); });
  document.getElementById("ref-clear").addEventListener("click", e => { e.stopPropagation(); clearRefFile(); });

  // CTA toggle
  const ctaToggle = document.getElementById("cta-toggle");
  const ctaInput = document.getElementById("cta-input");
  ctaToggle.addEventListener("change", () => {
    ctaInput.disabled = !ctaToggle.checked;
    ctaInput.style.opacity = ctaToggle.checked ? "1" : "0.3";
  });
}

function setRefFile(file) {
  refFile = file;
  const preview = document.getElementById("ref-preview");
  const text = document.getElementById("dropzone-text");
  const clearBtn = document.getElementById("ref-clear");
  preview.src = URL.createObjectURL(file);
  preview.hidden = false;
  text.hidden = true;
  clearBtn.hidden = false;
}

function clearRefFile() {
  refFile = null;
  document.getElementById("ref-preview").hidden = true;
  document.getElementById("dropzone-text").hidden = false;
  document.getElementById("ref-clear").hidden = true;
  document.getElementById("ref-input").value = "";
}

// ---------- Generate ----------

async function onGenerate(e) {
  e.preventDefault();
  const btn = document.getElementById("btn-generate");
  btn.disabled = true;
  btn.textContent = "Generating...";

  const fd = new FormData();
  fd.append("headline", formVal("headline"));
  fd.append("subhead", formVal("subhead"));
  const ctaOn = document.getElementById("cta-toggle").checked;
  fd.append("cta", ctaOn ? formVal("cta") : "");
  fd.append("bottom_strip_1", document.querySelector('[name="bottom_strip_1"]').value);
  fd.append("bottom_strip_2", document.querySelector('[name="bottom_strip_2"]').value);
  fd.append("bottom_strip_3", document.querySelector('[name="bottom_strip_3"]').value);

  const ings = [...document.querySelectorAll('#ingredients-list input:checked')].map(c => c.value);
  fd.append("ingredients", JSON.stringify(ings));

  const fmt = document.querySelector('[name="format"]:checked');
  fd.append("format", fmt ? fmt.value : "4:5");
  fd.append("template_hint", document.getElementById("template-select").value);
  fd.append("include_human", document.querySelector('[name="include_human"]').checked);

  if (refFile) fd.append("reference_image", refFile);

  const res = await fetch("/api/generate", { method: "POST", body: fd });
  const data = await res.json();
  currentRunId = data.run_id;
  renderedVariants = new Set();
  committedRatings = {};

  // Show progress, clear gallery
  document.getElementById("empty-state").hidden = true;
  document.getElementById("progress").hidden = false;
  document.getElementById("progress-fill").style.width = "0%";
  document.getElementById("progress-text").textContent = `0 / ${data.variant_count} variants`;
  document.getElementById("gallery").innerHTML = "";

  // Seed placeholder cards
  for (let i = 0; i < data.variant_count; i++) {
    const card = document.createElement("div");
    card.className = "variant-card loading";
    card.id = `card-${i}`;
    document.getElementById("gallery").appendChild(card);
  }

  // Start polling
  if (pollTimer) clearInterval(pollTimer);
  pollTimer = setInterval(() => pollStatus(data.variant_count), 3000);
}

function formVal(name) {
  const el = document.querySelector(`[name="${name}"]`);
  return el ? el.value : "";
}

// ---------- Polling ----------

async function pollStatus(total) {
  const res = await fetch(`/api/status/${currentRunId}`);
  const data = await res.json();

  const done = data.completed;
  document.getElementById("progress-fill").style.width = `${(done / total) * 100}%`;
  document.getElementById("progress-text").textContent = `${done} / ${total} variants`;

  data.variants.forEach(v => {
    if (v.status === "done" && !renderedVariants.has(v.index)) {
      renderCard(v.index, v.url);
      renderedVariants.add(v.index);
    }
    if (v.status === "error" && !renderedVariants.has(v.index)) {
      renderErrorCard(v.index, v.error);
      renderedVariants.add(v.index);
    }
  });

  if (done >= total) {
    clearInterval(pollTimer);
    document.getElementById("progress").hidden = true;
    document.getElementById("btn-generate").disabled = false;
    document.getElementById("btn-generate").textContent = "Generate 4 Variants";
  }
}

// ---------- Cards ----------

function renderCard(index, url) {
  const card = document.getElementById(`card-${index}`);
  card.className = "variant-card";
  card.innerHTML = `
    <a href="${url}" target="_blank"><img src="${url}" alt="Variant ${index + 1}" /></a>
    <div class="card-footer">
      <div>
        <div class="label">Variant ${index + 1}</div>
        <span class="approved-badge">Approved</span>
      </div>
      <div class="rating" data-index="${index}">
        ${[...Array(10)].map((_, i) => `<div class="dot" data-val="${i + 1}">${i + 1}</div>`).join("")}
      </div>
    </div>
  `;
  // Wire rating dots
  card.querySelectorAll(".dot").forEach(dot => {
    dot.addEventListener("click", () => rate(index, parseInt(dot.dataset.val)));
    dot.addEventListener("mouseenter", () => highlightDots(card, parseInt(dot.dataset.val)));
    dot.addEventListener("mouseleave", () => {
      // Revert to committed rating on mouse leave (not 0)
      highlightDots(card, committedRatings[index] || 0);
    });
  });
}

function renderErrorCard(index, error) {
  const card = document.getElementById(`card-${index}`);
  card.className = "variant-card error";
  card.dataset.error = error || "Generation failed";
}

function highlightDots(card, upTo) {
  card.querySelectorAll(".dot").forEach(d => {
    const v = parseInt(d.dataset.val);
    d.classList.toggle("filled", v <= upTo);
    d.classList.toggle("high", v <= upTo && v >= 8);
  });
}

async function rate(index, rating) {
  const card = document.getElementById(`card-${index}`);
  committedRatings[index] = rating;
  highlightDots(card, rating);

  try {
    const res = await fetch("/api/rate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ run_id: currentRunId, variant_index: index, rating }),
    });
    const data = await res.json();
    if (data.saved) {
      card.classList.add("approved");
    }
  } catch (err) {
    console.error("Rating failed:", err);
  }
}
