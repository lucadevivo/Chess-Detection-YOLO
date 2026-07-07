const $ = (id) => document.getElementById(id);
let stream = null;

async function listCameras() {
  // getUserMedia una volta per sbloccare le label dei device
  try {
    const tmp = await navigator.mediaDevices.getUserMedia({ video: true });
    tmp.getTracks().forEach((t) => t.stop());
  } catch (e) {
    $("status").textContent = "Permesso webcam negato: " + e.message;
    return;
  }
  const devices = await navigator.mediaDevices.enumerateDevices();
  const cams = devices.filter((d) => d.kind === "videoinput");
  const sel = $("camera");
  sel.innerHTML = "";
  cams.forEach((c, i) => {
    const o = document.createElement("option");
    o.value = c.deviceId;
    o.textContent = c.label || `Fotocamera ${i + 1}`;
    sel.appendChild(o);
  });
  sel.style.display = cams.length > 1 ? "" : "none"; // nascondi se una sola
  if (cams.length) startCamera(cams[0].deviceId);
}

async function startCamera(deviceId) {
  if (stream) stream.getTracks().forEach((t) => t.stop());
  stream = await navigator.mediaDevices.getUserMedia({
    video: { deviceId: deviceId ? { exact: deviceId } : undefined },
  });
  $("preview").srcObject = stream;
}

function captureBlob() {
  const v = $("preview");
  const cv = $("capture");
  cv.width = v.videoWidth;
  cv.height = v.videoHeight;
  cv.getContext("2d").drawImage(v, 0, 0);
  return new Promise((res) => cv.toBlob(res, "image/jpeg", 0.9));
}

function setEval(ev) {
  let pct = 50, label = "0.0";
  if (ev.mate != null) {
    pct = ev.mate > 0 ? 100 : 0;
    label = "M" + Math.abs(ev.mate);
  } else if (ev.cp != null) {
    const p = ev.cp / 100;              // pedoni
    const clamped = Math.max(-10, Math.min(10, p));
    pct = 50 + (clamped / 10) * 50;     // -10..10 -> 0..100
    label = (p >= 0 ? "+" : "") + p.toFixed(1);
  }
  $("eval-white").style.transform = "scaleY(" + pct / 100 + ")";
  $("eval-label").textContent = label;
}

function drawArrow(bestmove) {
  const c = $("arrow");
  const img = $("board");
  c.width = img.clientWidth;
  c.height = img.clientHeight;
  const ctx = c.getContext("2d");
  ctx.clearRect(0, 0, c.width, c.height);
  if (!bestmove || !bestmove.from) return;
  const cell = c.width / 8;
  const center = ([r, col]) => [col * cell + cell / 2, r * cell + cell / 2];
  const [x1, y1] = center(bestmove.from);
  const [x2, y2] = center(bestmove.to);
  ctx.strokeStyle = "rgba(255,140,0,.9)";
  ctx.fillStyle = "rgba(255,140,0,.9)";
  ctx.lineWidth = Math.max(3, cell * 0.12);
  ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke();
  const a = Math.atan2(y2 - y1, x2 - x1), h = cell * 0.35;
  ctx.beginPath();
  ctx.moveTo(x2, y2);
  ctx.lineTo(x2 - h * Math.cos(a - 0.4), y2 - h * Math.sin(a - 0.4));
  ctx.lineTo(x2 - h * Math.cos(a + 0.4), y2 - h * Math.sin(a + 0.4));
  ctx.closePath(); ctx.fill();
}

async function analyze() {
  $("analyze").disabled = true;
  $("status").textContent = "Analisi...";
  try {
    const blob = await captureBlob();
    const fd = new FormData();
    fd.append("image", blob, "frame.jpg");
    fd.append("white_side", $("white_side").value);
    fd.append("turn", $("turn").value);
    const r = await fetch("/analyze", { method: "POST", body: fd });
    const body = await r.json();
    // mostra comunque la board 2D se disponibile (anche in errore)
    if (body.board && body.board.png_b64) {
      $("board").onload = () => drawArrow(body.ok ? body.bestmove : null);
      $("board").src = "data:image/png;base64," + body.board.png_b64;
    }
    if (!body.ok) {
      const msg = { corner: "Riquadra bene la scacchiera (4 marker).",
                    fen: "Posizione non valida: " + (body.detail || ""),
                    engine: "Motore non disponibile: " + (body.detail || ""),
                    image: "Immagine non valida." };
      $("status").textContent = msg[body.reason] || body.detail || "Errore.";
      setEval({ cp: null, mate: null });
      $("bestmove").textContent = "";
      return;
    }
    $("status").textContent = "";
    setEval(body.eval);
    $("bestmove").textContent = "Mossa migliore: " + (body.bestmove.uci || "-");
  } catch (e) {
    $("status").textContent = "Errore: " + e.message;
  } finally {
    $("analyze").disabled = false;
  }
}

$("camera").addEventListener("change", (e) => startCamera(e.target.value));
$("analyze").addEventListener("click", analyze);
listCameras();
