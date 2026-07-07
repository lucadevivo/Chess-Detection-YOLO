const $ = (id) => document.getElementById(id);

// marker: nome backend -> simbolo + posizione di fallback (frazionaria) se YOLO non lo trova
const MARKERS = [
  { name: "L-corner", sym: "L", fx: 0.80, fy: 0.20 },
  { name: "star-corner", sym: "★", fx: 0.80, fy: 0.80 },
  { name: "square-corner", sym: "■", fy: 0.80, fx: 0.20 },
  { name: "triangle-corner", sym: "▲", fx: 0.20, fy: 0.20 },
];

const state = {
  stream: null,
  blob: null,            // JPEG del frame catturato
  frameW: 0, frameH: 0,  // risoluzione reale del frame
  handles: {},           // name -> {x, y} in frazione 0..1
  white_side: "bottom",
  turn: "w",
};

/* ---------- fotocamera ---------- */
async function listCameras() {
  try {
    const tmp = await navigator.mediaDevices.getUserMedia({ video: true });
    tmp.getTracks().forEach((t) => t.stop());
  } catch (e) {
    setStatus("Permesso webcam negato: " + e.message, "err");
    return;
  }
  const cams = (await navigator.mediaDevices.enumerateDevices()).filter((d) => d.kind === "videoinput");
  const sel = $("camera");
  sel.innerHTML = "";
  cams.forEach((c, i) => {
    const o = document.createElement("option");
    o.value = c.deviceId;
    o.textContent = c.label || `Fotocamera ${i + 1}`;
    sel.appendChild(o);
  });
  $("cameraField").hidden = cams.length <= 1;   // mostra il picker solo se serve
  if (cams.length) startCamera(cams[0].deviceId);
}

async function startCamera(deviceId) {
  if (state.stream) state.stream.getTracks().forEach((t) => t.stop());
  state.stream = await navigator.mediaDevices.getUserMedia({
    video: { deviceId: deviceId ? { exact: deviceId } : undefined, width: { ideal: 1280 } },
  });
  $("preview").srcObject = state.stream;
}

/* ---------- cattura + calibrazione ---------- */
function frameToBlob() {
  const v = $("preview");
  const cv = $("capbuf");
  cv.width = v.videoWidth; cv.height = v.videoHeight;
  cv.getContext("2d").drawImage(v, 0, 0);
  state.frameW = cv.width; state.frameH = cv.height;
  return new Promise((res) => cv.toBlob(res, "image/jpeg", 0.92));
}

async function capture() {
  setStatus("Rilevo gli angoli…");
  $("capture").disabled = true;
  try {
    state.blob = await frameToBlob();
    $("still").src = URL.createObjectURL(state.blob);
    $("still").hidden = false;
    $("preview").hidden = true;

    // pre-posiziona i punti dai corner rilevati da YOLO
    const fd = new FormData();
    fd.append("image", state.blob, "f.jpg");
    let corners = {};
    try {
      const r = await fetch("/detect_corners", { method: "POST", body: fd });
      const b = await r.json();
      if (b.ok) corners = b.corners;
    } catch (_) { /* offline: uso i fallback */ }

    state.handles = {};
    for (const m of MARKERS) {
      if (corners[m.name]) {
        state.handles[m.name] = { x: corners[m.name][0] / state.frameW, y: corners[m.name][1] / state.frameH };
      } else {
        state.handles[m.name] = { x: m.fx, y: m.fy };
      }
    }
    renderHandles();
    $("handles").hidden = false;
    $("capture").hidden = true;
    $("recapture").hidden = false;
    $("analyze").hidden = false;
    const found = Object.keys(corners).length;
    setStatus(found === 4
      ? "Angoli rilevati. Trascina i punti per rifinire, poi Analizza."
      : `Rilevati ${found}/4 angoli. Trascina i punti mancanti sugli angoli, poi Analizza.`,
      found === 4 ? "ok" : "");
  } catch (e) {
    setStatus("Errore cattura: " + e.message, "err");
  } finally {
    $("capture").disabled = false;
  }
}

function recapture() {
  $("still").removeAttribute("src");
  $("still").hidden = true;
  $("preview").hidden = false;
  $("handles").hidden = true;
  $("handles").querySelectorAll(".handle").forEach((h) => h.remove());
  $("capture").hidden = false;
  $("recapture").hidden = true;
  $("analyze").hidden = true;
  setStatus("");
}

function renderHandles() {
  const layer = $("handles");
  layer.querySelectorAll(".handle").forEach((h) => h.remove());
  for (const m of MARKERS) {
    const p = state.handles[m.name];
    const el = document.createElement("div");
    el.className = "handle";
    el.style.left = p.x * 100 + "%";
    el.style.top = p.y * 100 + "%";
    el.innerHTML = `<span>${m.sym}</span>`;
    el.title = m.name;
    el.addEventListener("pointerdown", (ev) => startDrag(ev, m.name, el));
    layer.appendChild(el);
  }
  drawFrameline();
}

function drawFrameline() {
  const rect = $("stage").getBoundingClientRect();
  const pts = MARKERS.map((m) => {
    const p = state.handles[m.name];
    return `${p.x * rect.width},${p.y * rect.height}`;
  }).join(" ");
  $("frameline").querySelector("polygon").setAttribute("points", pts);
}

function startDrag(ev, name, el) {
  ev.preventDefault();
  el.setPointerCapture(ev.pointerId);
  const stage = $("stage");
  const move = (e) => {
    const rect = stage.getBoundingClientRect();
    let x = (e.clientX - rect.left) / rect.width;
    let y = (e.clientY - rect.top) / rect.height;
    x = Math.min(1, Math.max(0, x)); y = Math.min(1, Math.max(0, y));
    state.handles[name] = { x, y };
    el.style.left = x * 100 + "%"; el.style.top = y * 100 + "%";
    drawFrameline();
  };
  const up = (e) => {
    el.releasePointerCapture(ev.pointerId);
    el.removeEventListener("pointermove", move);
    el.removeEventListener("pointerup", up);
  };
  el.addEventListener("pointermove", move);
  el.addEventListener("pointerup", up);
}

/* ---------- analisi ---------- */
async function analyze() {
  $("analyze").disabled = true;
  setStatus("Analisi in corso…");
  try {
    const corners = {};
    for (const m of MARKERS) {
      const p = state.handles[m.name];
      corners[m.name] = [Math.round(p.x * state.frameW), Math.round(p.y * state.frameH)];
    }
    const fd = new FormData();
    fd.append("image", state.blob, "f.jpg");
    fd.append("white_side", state.white_side);
    fd.append("turn", state.turn);
    fd.append("corners", JSON.stringify(corners));

    const r = await fetch("/analyze", { method: "POST", body: fd });
    const b = await r.json();

    if (b.board && b.board.png_b64) showBoard(b.board.png_b64, b.ok ? b.bestmove : null);
    if (!b.ok) {
      const msg = {
        corner: "Angoli non validi: sistema i 4 punti sulla scacchiera.",
        fen: "Posizione non valida: " + (b.detail || "controlla pezzi e turno."),
        engine: "Motore non disponibile.",
        image: "Immagine non valida.",
      };
      setStatus(msg[b.reason] || b.detail || "Errore.", "err");
      setEval({ cp: null, mate: null });
      $("score").textContent = "—"; $("best").textContent = ""; $("fen").textContent = "";
      return;
    }
    setStatus("");
    setEval(b.eval);
    $("best").innerHTML = "Mossa migliore: <b>" + (b.bestmove.uci || "-") + "</b>";
    $("fen").textContent = b.fen;
  } catch (e) {
    setStatus("Errore: " + e.message, "err");
  } finally {
    $("analyze").disabled = false;
  }
}

function showBoard(pngB64, bestmove) {
  $("boardEmpty").style.display = "none";
  const img = $("board");
  img.onload = () => drawArrow(bestmove);
  img.src = "data:image/png;base64," + pngB64;
}

function setEval(ev) {
  let pct = 50, label = "0.0";
  if (ev.mate != null) { pct = ev.mate > 0 ? 100 : 0; label = "M" + Math.abs(ev.mate); }
  else if (ev.cp != null) {
    const p = ev.cp / 100, c = Math.max(-10, Math.min(10, p));
    pct = 50 + (c / 10) * 50; label = (p >= 0 ? "+" : "") + p.toFixed(1);
  } else { $("score").textContent = "—"; }
  $("evalWhite").style.transform = "scaleY(" + pct / 100 + ")";
  if (ev.cp != null || ev.mate != null) $("score").textContent = label;
}

function drawArrow(bestmove) {
  const c = $("arrow"), img = $("board");
  c.width = img.clientWidth; c.height = img.clientHeight;
  const ctx = c.getContext("2d");
  ctx.clearRect(0, 0, c.width, c.height);
  if (!bestmove || !bestmove.from) return;
  const cell = c.width / 8;
  const center = ([r, col]) => [col * cell + cell / 2, r * cell + cell / 2];
  const [fx, fy] = center(bestmove.from), [tx, ty] = center(bestmove.to);
  const ang = Math.atan2(ty - fy, tx - fx);
  const dist = Math.hypot(tx - fx, ty - fy);

  // proporzioni stile chess.com
  const shaft = cell * 0.28, headW = cell * 0.62, headL = cell * 0.52;
  const gap = cell * 0.30;                 // parte poco dopo il centro casella
  const len = Math.max(headL, dist - gap);
  const body = Math.max(0, len - headL);
  const x0 = fx + Math.cos(ang) * gap, y0 = fy + Math.sin(ang) * gap;

  // poligono asta+testa in coordinate locali (x = direzione), poi ruotato
  const pts = [
    [0, -shaft / 2], [body, -shaft / 2], [body, -headW / 2],
    [len, 0], [body, headW / 2], [body, shaft / 2], [0, shaft / 2],
  ];
  ctx.save();
  ctx.translate(x0, y0); ctx.rotate(ang);
  ctx.lineJoin = "round";
  ctx.beginPath();
  pts.forEach(([px, py], i) => (i ? ctx.lineTo(px, py) : ctx.moveTo(px, py)));
  ctx.closePath();
  ctx.fillStyle = "rgba(255, 170, 0, 0.82)";   // arancio chess.com
  ctx.fill();
  ctx.restore();
}

/* ---------- ui plumbing ---------- */
function setStatus(msg, kind) { const s = $("status"); s.textContent = msg; s.className = "status" + (kind ? " " + kind : ""); }

function bindSeg(id, key) {
  $(id).addEventListener("click", (e) => {
    const btn = e.target.closest("button"); if (!btn) return;
    state[key] = btn.dataset.v;
    $(id).querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", b === btn));
  });
}

$("camera").addEventListener("change", (e) => startCamera(e.target.value));
$("capture").addEventListener("click", capture);
$("recapture").addEventListener("click", recapture);
$("analyze").addEventListener("click", analyze);
bindSeg("white_side", "white_side");
bindSeg("turn", "turn");
window.addEventListener("resize", () => { if (!$("handles").hidden) drawFrameline(); });
listCameras();
