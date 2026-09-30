"""
Attendance Certificate Generator
--------------------------------
A single-file Flask app. Everything (HTML, CSS, JS) is embedded below.

Run:
    pip install flask
    python app.py
Then open http://127.0.0.1:5000

Notes
-----
* The background image never leaves the browser: it is read with FileReader /
  object URLs, so no server-side upload handling or static folder is needed.
* PNG export uses a plain <canvas> at the image's full resolution.
* PDF export embeds that canvas as a JPEG inside a hand-built PDF, so there are
  no external JS libraries (no html2canvas / jsPDF) and it works offline.
* Google Fonts are loaded as an optional nicety. If they cannot be reached the
  font stacks fall back to system fonts, and export still works.
"""

from flask import Flask, render_template_string

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

PAGE = r"""
{% raw %}
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Attendance Certificate Generator</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Amiri:wght@400;700&family=Cairo:wght@400;700&family=Cormorant+Garamond:wght@500;700&family=Great+Vibes&family=Playfair+Display:wght@500;700&display=swap" rel="stylesheet">
<style>
  :root {
    --ink: #1d2733;
    --ink-soft: #55616f;
    --paper: #f6f4ef;
    --panel: #ffffff;
    --line: #d9d5cb;
    --accent: #0f6b66;
    --accent-dark: #0a4f4b;
    --danger: #a3302a;
    --radius: 10px;
  }
  * { box-sizing: border-box; }
  html, body { margin: 0; }
  body {
    font-family: "Segoe UI", Tahoma, Arial, sans-serif;
    color: var(--ink);
    background: var(--paper);
    line-height: 1.5;
  }
  header {
    padding: 22px clamp(16px, 4vw, 40px) 8px;
  }
  header h1 {
    margin: 0;
    font-family: "Cormorant Garamond", Georgia, serif;
    font-size: clamp(1.7rem, 3.4vw, 2.3rem);
    font-weight: 700;
    letter-spacing: .2px;
  }
  header p { margin: 4px 0 0; color: var(--ink-soft); max-width: 62ch; }

  main {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 340px;
    gap: 24px;
    padding: 16px clamp(16px, 4vw, 40px) 40px;
    align-items: start;
  }
  @media (max-width: 900px) {
    main { grid-template-columns: minmax(0, 1fr); }
  }

  /* ---------- Stage ---------- */
  .stage-wrap {
    background: var(--panel);
    border: 1px solid var(--line);
    border-radius: var(--radius);
    padding: 14px;
  }
  .dropzone {
    border: 2px dashed var(--line);
    border-radius: var(--radius);
    min-height: 260px;
    display: grid;
    place-items: center;
    text-align: center;
    padding: 28px 18px;
    cursor: pointer;
    transition: border-color .15s, background .15s;
    color: var(--ink-soft);
  }
  .dropzone:hover, .dropzone:focus-visible, .dropzone.over {
    border-color: var(--accent);
    background: #eef6f5;
    outline: none;
  }
  .dropzone strong { display: block; color: var(--ink); font-size: 1.1rem; margin-bottom: 4px; }
  .dropzone small { display: block; margin-top: 10px; }
  .link-btn {
    background: none; border: 0; padding: 0; color: var(--accent);
    text-decoration: underline; cursor: pointer; font: inherit;
  }

  .stage {
    position: relative;
    width: 100%;
    line-height: 0;
    user-select: none;
    -webkit-user-select: none;
    touch-action: none;
    border-radius: 4px;
    overflow: hidden;
    box-shadow: 0 1px 0 var(--line), 0 10px 28px rgba(29, 39, 51, .14);
  }
  .stage img {
    width: 100%;
    height: auto;
    display: block;
    pointer-events: none;
    -webkit-user-drag: none;
  }
  .name-tag {
    position: absolute;
    left: 50%;
    top: 55%;
    transform: translate(-50%, -50%);
    white-space: nowrap;
    line-height: 1.2;
    cursor: grab;
    padding: 2px 10px;
    outline: 1px dashed transparent;
    outline-offset: 2px;
    touch-action: none;
  }
  .name-tag:hover, .name-tag.dragging { outline-color: var(--accent); }
  .name-tag.dragging { cursor: grabbing; }

  .stage-bar {
    display: flex; flex-wrap: wrap; gap: 10px; justify-content: space-between;
    align-items: center; margin-top: 12px; color: var(--ink-soft); font-size: .9rem;
  }

  /* ---------- Controls ---------- */
  .panel {
    background: var(--panel);
    border: 1px solid var(--line);
    border-radius: var(--radius);
    padding: 18px;
    display: grid;
    gap: 16px;
  }
  .field { display: grid; gap: 6px; }
  .field > label, .field > .label { font-weight: 600; font-size: .92rem; }
  input[type="text"], select {
    width: 100%;
    padding: 10px 12px;
    border: 1px solid var(--line);
    border-radius: 8px;
    font: inherit;
    background: #fff;
    color: var(--ink);
  }
  input[type="text"]:focus, select:focus, input[type="range"]:focus-visible,
  input[type="color"]:focus-visible, button:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: 2px;
  }
  .row { display: flex; align-items: center; gap: 10px; }
  .row input[type="range"] { flex: 1; }
  .value { min-width: 4.2ch; text-align: right; font-variant-numeric: tabular-nums; color: var(--ink-soft); }
  input[type="color"] {
    width: 48px; height: 38px; padding: 2px; border: 1px solid var(--line);
    border-radius: 8px; background: #fff; cursor: pointer;
  }
  .swatches { display: flex; gap: 6px; flex-wrap: wrap; }
  .swatch {
    width: 26px; height: 26px; border-radius: 50%; border: 2px solid #fff;
    box-shadow: 0 0 0 1px var(--line); cursor: pointer; padding: 0;
  }

  .btn {
    font: inherit; font-weight: 600; cursor: pointer;
    padding: 11px 14px; border-radius: 8px; border: 1px solid var(--accent);
    background: var(--accent); color: #fff; transition: background .15s;
  }
  .btn:hover:not(:disabled) { background: var(--accent-dark); }
  .btn.secondary { background: #fff; color: var(--accent); }
  .btn.secondary:hover:not(:disabled) { background: #eef6f5; }
  .btn:disabled { opacity: .45; cursor: not-allowed; }
  .btn-row { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }

  .status { min-height: 1.3em; font-size: .9rem; color: var(--ink-soft); }
  .status.error { color: var(--danger); }
  .hint { font-size: .85rem; color: var(--ink-soft); margin: 0; }
  .hidden { display: none !important; }
  input[type="file"] { display: none; }
</style>
</head>
<body>
<header>
  <h1>Attendance certificate generator</h1>
  <p>Upload a certificate background, type the participant's name, drag it into place, then download a PNG or PDF. Everything happens in your browser.</p>
</header>

<main>
  <section class="stage-wrap" aria-label="Certificate preview">
    <div id="dropzone" class="dropzone" tabindex="0" role="button"
         aria-label="Upload a certificate background image">
      <div>
        <strong>Drop your certificate background here</strong>
        or <button type="button" class="link-btn" id="browseBtn">browse for a file</button>
        <small>PNG or JPG. Or <button type="button" class="link-btn" id="sampleBtn">use a sample background</button> to try the tool.</small>
      </div>
    </div>

    <div id="stage" class="stage hidden">
      <img id="bgImg" alt="Certificate background preview">
      <div id="nameTag" class="name-tag" role="slider" tabindex="0"
           aria-label="Participant name. Drag to reposition, or use arrow keys.">Participant Name</div>
    </div>

    <div id="stageBar" class="stage-bar hidden">
      <span id="imgInfo"></span>
      <span><button type="button" class="link-btn" id="replaceBtn">Replace image</button>
        &nbsp;|&nbsp;<button type="button" class="link-btn" id="centerBtn">Center name</button></span>
    </div>

    <input type="file" id="fileInput" accept="image/png,image/jpeg">
  </section>

  <aside class="panel" aria-label="Certificate controls">
    <div class="field">
      <label for="nameInput">Participant name</label>
      <input type="text" id="nameInput" dir="auto" value="Participant Name" autocomplete="off">
    </div>

    <div class="field">
      <label for="fontFamily">Font family</label>
      <select id="fontFamily">
        <option value="'Playfair Display', Georgia, serif">Playfair Display</option>
        <option value="'Cormorant Garamond', Georgia, serif">Cormorant Garamond</option>
        <option value="'Great Vibes', 'Brush Script MT', cursive">Great Vibes (script)</option>
        <option value="Georgia, 'Times New Roman', serif">Georgia</option>
        <option value="'Times New Roman', Times, serif">Times New Roman</option>
        <option value="Arial, Helvetica, sans-serif">Arial</option>
        <option value="'Trebuchet MS', Tahoma, sans-serif">Trebuchet MS</option>
        <option value="Verdana, Geneva, sans-serif">Verdana</option>
        <option value="'Courier New', monospace">Courier New</option>
        <option value="Amiri, 'Times New Roman', serif">Amiri (Arabic serif)</option>
        <option value="Cairo, Tahoma, sans-serif">Cairo (Arabic sans)</option>
      </select>
    </div>

    <div class="field">
      <label for="fontSize">Font size</label>
      <div class="row">
        <input type="range" id="fontSize" min="10" max="400" value="80">
        <span class="value" id="fontSizeVal">80 px</span>
      </div>
      <p class="hint">Sized in pixels of the original image, so the export matches the preview.</p>
    </div>

    <div class="field">
      <span class="label">Font color</span>
      <div class="row">
        <input type="color" id="fontColor" value="#1d2733" aria-label="Font color">
        <div class="swatches" id="swatches"></div>
      </div>
    </div>

    <div class="field">
      <span class="label">Export</span>
      <div class="btn-row">
        <button type="button" class="btn" id="pngBtn" disabled>Download PNG</button>
        <button type="button" class="btn secondary" id="pdfBtn" disabled>Download PDF</button>
      </div>
    </div>
    <div class="status" id="status" role="status" aria-live="polite"></div>
  </aside>
</main>

<script>
(function () {
  "use strict";

  // ---------- Elements ----------
  var $ = function (id) { return document.getElementById(id); };
  var dropzone = $("dropzone"), fileInput = $("fileInput"), stage = $("stage");
  var stageBar = $("stageBar"), bgImg = $("bgImg"), nameTag = $("nameTag");
  var nameInput = $("nameInput"), fontFamily = $("fontFamily"), fontSize = $("fontSize");
  var fontSizeVal = $("fontSizeVal"), fontColor = $("fontColor"), statusEl = $("status");
  var pngBtn = $("pngBtn"), pdfBtn = $("pdfBtn"), imgInfo = $("imgInfo");

  // ---------- State ----------
  var state = {
    loaded: false,
    natW: 0, natH: 0,
    x: 0.5, y: 0.55,          // text centre as a fraction of the image (0..1)
    objectUrl: null
  };

  // ---------- Helpers ----------
  function setStatus(msg, isError) {
    statusEl.textContent = msg || "";
    statusEl.classList.toggle("error", !!isError);
  }
  function isRtl(text) { return /[\u0590-\u08FF\uFB1D-\uFDFF\uFE70-\uFEFF]/.test(text); }
  function currentText() { return nameInput.value.trim() || "Participant Name"; }
  function clamp(v, a, b) { return Math.min(b, Math.max(a, v)); }
  function safeFileName() {
    var base = currentText().replace(/[\\/:*?"<>|]+/g, "").replace(/\s+/g, "-").slice(0, 60);
    return "certificate-" + (base || "participant");
  }

  // ---------- Swatches ----------
  ["#1d2733", "#000000", "#0f6b66", "#8a1c2b", "#1f3f8f", "#9a6b00", "#ffffff"].forEach(function (c) {
    var b = document.createElement("button");
    b.type = "button"; b.className = "swatch"; b.style.background = c;
    b.setAttribute("aria-label", "Use color " + c);
    b.addEventListener("click", function () { fontColor.value = c; render(); });
    $("swatches").appendChild(b);
  });

  // ---------- Loading an image ----------
  function loadFromUrl(url, label, revokeLater) {
    var probe = new Image();
    probe.onload = function () {
      if (state.objectUrl && state.objectUrl !== url) URL.revokeObjectURL(state.objectUrl);
      state.objectUrl = revokeLater ? url : null;
      state.natW = probe.naturalWidth;
      state.natH = probe.naturalHeight;
      state.loaded = true;
      bgImg.src = url;
      dropzone.classList.add("hidden");
      stage.classList.remove("hidden");
      stageBar.classList.remove("hidden");
      imgInfo.textContent = label + " (" + state.natW + " x " + state.natH + " px)";

      // Sensible defaults relative to image size
      fontSize.max = Math.round(state.natW / 4);
      fontSize.value = Math.round(state.natW / 18);
      state.x = 0.5; state.y = 0.55;
      pngBtn.disabled = false; pdfBtn.disabled = false;
      setStatus("Image loaded. Drag the name to position it.");
      render();
    };
    probe.onerror = function () {
      setStatus("That file could not be read as an image. Try a PNG or JPG.", true);
    };
    probe.src = url;
  }

  function handleFile(file) {
    if (!file) return;
    if (!/^image\/(png|jpeg)$/.test(file.type)) {
      setStatus("Unsupported file type. Please choose a PNG or JPG image.", true);
      return;
    }
    loadFromUrl(URL.createObjectURL(file), file.name, true);
  }

  // Generates a simple landscape sample so the tool can be tried without a file.
  function makeSample() {
    var c = document.createElement("canvas");
    c.width = 1600; c.height = 1131;
    var g = c.getContext("2d");
    g.fillStyle = "#fbf8f1"; g.fillRect(0, 0, c.width, c.height);
    g.strokeStyle = "#0f6b66"; g.lineWidth = 14; g.strokeRect(50, 50, c.width - 100, c.height - 100);
    g.strokeStyle = "#c9a24b"; g.lineWidth = 4; g.strokeRect(80, 80, c.width - 160, c.height - 160);
    g.fillStyle = "#1d2733"; g.textAlign = "center"; g.textBaseline = "middle";
    g.font = "700 96px Georgia, serif"; g.fillText("Certificate of Attendance", c.width / 2, 300);
    g.font = "400 38px Georgia, serif"; g.fillText("This certifies that", c.width / 2, 430);
    g.fillText("attended the workshop in full", c.width / 2, 760);
    g.font = "400 30px Georgia, serif";
    g.fillText("Date: ______________", 430, 960);
    g.fillText("Signature: ______________", 1130, 960);
    c.toBlob(function (blob) {
      loadFromUrl(URL.createObjectURL(blob), "Sample background", true);
    }, "image/png");
  }

  // ---------- Dropzone wiring ----------
  $("browseBtn").addEventListener("click", function (e) { e.stopPropagation(); fileInput.click(); });
  $("sampleBtn").addEventListener("click", function (e) { e.stopPropagation(); makeSample(); });
  $("replaceBtn").addEventListener("click", function () { fileInput.click(); });
  $("centerBtn").addEventListener("click", function () { state.x = 0.5; render(); });
  dropzone.addEventListener("click", function () { fileInput.click(); });
  dropzone.addEventListener("keydown", function (e) {
    if (e.key === "Enter" || e.key === " ") { e.preventDefault(); fileInput.click(); }
  });
  fileInput.addEventListener("change", function () {
    handleFile(fileInput.files[0]);
    fileInput.value = "";
  });

  // Accept drops on the dropzone and, once loaded, anywhere over the stage panel.
  var dropTargets = [dropzone, document.querySelector(".stage-wrap")];
  dropTargets.forEach(function (el) {
    ["dragenter", "dragover"].forEach(function (ev) {
      el.addEventListener(ev, function (e) {
        if (!e.dataTransfer || Array.prototype.indexOf.call(e.dataTransfer.types || [], "Files") === -1) return;
        e.preventDefault(); dropzone.classList.add("over");
      });
    });
    ["dragleave", "drop"].forEach(function (ev) {
      el.addEventListener(ev, function () { dropzone.classList.remove("over"); });
    });
    el.addEventListener("drop", function (e) {
      e.preventDefault();
      var f = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
      handleFile(f);
    });
  });
  // Stop the browser from navigating away if a file is dropped outside the zones.
  window.addEventListener("dragover", function (e) { e.preventDefault(); });
  window.addEventListener("drop", function (e) { e.preventDefault(); });

  // ---------- Rendering the live preview ----------
  function displayScale() {
    return state.natW ? stage.clientWidth / state.natW : 1;
  }
  function render() {
    var text = currentText();
    var size = parseInt(fontSize.value, 10);
    fontSizeVal.textContent = size + " px";
    nameTag.textContent = text;
    nameTag.style.fontFamily = fontFamily.value;
    nameTag.style.color = fontColor.value;
    nameTag.style.direction = isRtl(text) ? "rtl" : "ltr";
    nameTag.style.fontSize = (size * displayScale()) + "px";
    nameTag.style.left = (state.x * 100) + "%";
    nameTag.style.top = (state.y * 100) + "%";
  }
  [nameInput, fontFamily, fontSize, fontColor].forEach(function (el) {
    el.addEventListener("input", render);
    el.addEventListener("change", render);
  });
  window.addEventListener("resize", render);
  if (window.ResizeObserver) new ResizeObserver(render).observe(stage);

  // ---------- Dragging the name (mouse, touch and pen via Pointer Events) ----------
  var drag = null;
  nameTag.addEventListener("pointerdown", function (e) {
    if (!state.loaded) return;
    e.preventDefault();
    var rect = stage.getBoundingClientRect();
    drag = {
      dx: e.clientX - (rect.left + state.x * rect.width),
      dy: e.clientY - (rect.top + state.y * rect.height)
    };
    nameTag.setPointerCapture(e.pointerId);
    nameTag.classList.add("dragging");
  });
  nameTag.addEventListener("pointermove", function (e) {
    if (!drag) return;
    var rect = stage.getBoundingClientRect();
    state.x = clamp((e.clientX - drag.dx - rect.left) / rect.width, 0, 1);
    state.y = clamp((e.clientY - drag.dy - rect.top) / rect.height, 0, 1);
    render();
  });
  function endDrag(e) {
    if (!drag) return;
    drag = null;
    nameTag.classList.remove("dragging");
    try { nameTag.releasePointerCapture(e.pointerId); } catch (err) { /* already released */ }
  }
  nameTag.addEventListener("pointerup", endDrag);
  nameTag.addEventListener("pointercancel", endDrag);

  // Keyboard nudging for accessibility
  nameTag.addEventListener("keydown", function (e) {
    var step = e.shiftKey ? 0.02 : 0.005;
    var moved = true;
    if (e.key === "ArrowLeft") state.x = clamp(state.x - step, 0, 1);
    else if (e.key === "ArrowRight") state.x = clamp(state.x + step, 0, 1);
    else if (e.key === "ArrowUp") state.y = clamp(state.y - step, 0, 1);
    else if (e.key === "ArrowDown") state.y = clamp(state.y + step, 0, 1);
    else moved = false;
    if (moved) { e.preventDefault(); render(); }
  });

  // ---------- Exporting ----------
  // Draws the certificate at the image's native resolution.
  function drawCertificate() {
    var canvas = document.createElement("canvas");
    canvas.width = state.natW;
    canvas.height = state.natH;
    var ctx = canvas.getContext("2d");
    // White underlay so transparent PNGs also export cleanly as JPEG inside the PDF.
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(bgImg, 0, 0, canvas.width, canvas.height);

    var text = currentText();
    var size = parseInt(fontSize.value, 10);
    ctx.font = size + "px " + fontFamily.value;
    ctx.fillStyle = fontColor.value;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.direction = isRtl(text) ? "rtl" : "ltr";
    ctx.fillText(text, state.x * canvas.width, state.y * canvas.height);
    return canvas;
  }

  // Make sure the chosen web font is ready before painting it to the canvas.
  function ensureFont() {
    if (!document.fonts || !document.fonts.load) return Promise.resolve();
    var size = parseInt(fontSize.value, 10);
    return document.fonts.load(size + "px " + fontFamily.value, currentText()).catch(function () {});
  }

  function download(blob, filename) {
    var url = URL.createObjectURL(blob);
    var a = document.createElement("a");
    a.href = url; a.download = filename;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(function () { URL.revokeObjectURL(url); }, 2000);
  }

  function canvasToBlob(canvas, type, quality) {
    return new Promise(function (resolve, reject) {
      canvas.toBlob(function (b) { b ? resolve(b) : reject(new Error("Canvas export failed")); }, type, quality);
    });
  }

  function exportPng() {
    if (!state.loaded) return;
    setStatus("Preparing PNG...");
    ensureFile_then(function (canvas) {
      return canvasToBlob(canvas, "image/png").then(function (blob) {
        download(blob, safeFileName() + ".png");
        setStatus("PNG downloaded.");
      });
    });
  }

  // Minimal PDF writer: one page, one JPEG image that fills the page.
  function buildPdf(jpegBytes, imgW, imgH) {
    var enc = new TextEncoder();
    var longSide = 842;                                   // points (A4 long edge)
    var pw, ph;
    if (imgW >= imgH) { pw = longSide; ph = longSide * imgH / imgW; }
    else { ph = longSide; pw = longSide * imgW / imgH; }
    pw = Math.round(pw * 100) / 100; ph = Math.round(ph * 100) / 100;

    var chunks = [], offsets = [], length = 0;
    function push(d) {
      var b = typeof d === "string" ? enc.encode(d) : d;
      chunks.push(b); length += b.length;
    }
    push("%PDF-1.4\n%\xE2\xE3\xCF\xD3\n");

    offsets[1] = length; push("1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n");
    offsets[2] = length; push("2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n");
    offsets[3] = length;
    push("3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 " + pw + " " + ph + "] " +
         "/Resources << /XObject << /Im0 4 0 R >> >> /Contents 5 0 R >>\nendobj\n");
    offsets[4] = length;
    push("4 0 obj\n<< /Type /XObject /Subtype /Image /Width " + imgW + " /Height " + imgH +
         " /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length " +
         jpegBytes.length + " >>\nstream\n");
    push(jpegBytes);
    push("\nendstream\nendobj\n");
    var content = "q " + pw + " 0 0 " + ph + " 0 0 cm /Im0 Do Q";
    offsets[5] = length;
    push("5 0 obj\n<< /Length " + content.length + " >>\nstream\n" + content + "\nendstream\nendobj\n");

    var xrefPos = length;
    var xref = "xref\n0 6\n0000000000 65535 f \n";
    for (var i = 1; i <= 5; i++) xref += ("0000000000" + offsets[i]).slice(-10) + " 00000 n \n";
    push(xref);
    push("trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n" + xrefPos + "\n%%EOF");

    return new Blob(chunks, { type: "application/pdf" });
  }

  function exportPdf() {
    if (!state.loaded) return;
    setStatus("Preparing PDF...");
    ensureFile_then(function (canvas) {
      return canvasToBlob(canvas, "image/jpeg", 0.95)
        .then(function (b) { return b.arrayBuffer(); })
        .then(function (buf) {
          var pdf = buildPdf(new Uint8Array(buf), canvas.width, canvas.height);
          download(pdf, safeFileName() + ".pdf");
          setStatus("PDF downloaded.");
        });
    });
  }

  // Shared wrapper: wait for fonts, draw, run the export step, report errors.
  function ensureFile_then(step) {
    pngBtn.disabled = pdfBtn.disabled = true;
    ensureFont()
      .then(function () { return step(drawCertificate()); })
      .catch(function (err) {
        console.error(err);
        setStatus("Export failed: " + (err && err.message ? err.message : "unknown error") +
                  ". Very large images can exceed browser canvas limits; try a smaller one.", true);
      })
      .then(function () { pngBtn.disabled = pdfBtn.disabled = !state.loaded; });
  }

  pngBtn.addEventListener("click", exportPng);
  pdfBtn.addEventListener("click", exportPdf);

  render();
})();
</script>
</body>
</html>
{% endraw %}
"""


@app.route("/")
def index():
    return render_template_string(PAGE)


if __name__ == "__main__":
    app.run(debug=True)