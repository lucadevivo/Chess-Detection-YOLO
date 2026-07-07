"""FastAPI: serve il frontend e l'endpoint /analyze."""
import base64
import json
import os
import sys

import cv2
import numpy as np
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

_SRC = os.path.join(os.path.dirname(__file__), "..", "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)
import graphics  # noqa: E402  (src/graphics.py)

from web import board, detect, engine  # noqa: E402

HERE = os.path.dirname(__file__)
STATIC = os.path.join(HERE, "static")
MODEL_PATH = os.path.join(HERE, "..", "best.pt")

app = FastAPI(title="Chess Vision")
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.on_event("startup")
def _startup():
    detect.load_model(MODEL_PATH)


@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC, "index.html"))


def _decode(raw):
    arr = np.frombuffer(raw, np.uint8)
    return cv2.imdecode(arr, cv2.IMREAD_COLOR)


@app.post("/detect_corners")
async def detect_corners(image: UploadFile = File(...)):
    """Rileva i 4 marker d'angolo per pre-posizionare i punti trascinabili."""
    frame = _decode(await image.read())
    if frame is None:
        return JSONResponse({"ok": False, "reason": "image"})
    det = detect.detect(frame)
    corners = {name: [int(x), int(y)] for name, (x, y) in det["corners"].items()}
    h, w = frame.shape[:2]
    return JSONResponse({"ok": True, "corners": corners, "size": [w, h]})


@app.post("/analyze")
async def analyze(image: UploadFile = File(...),
                  white_side: str = Form(...),
                  turn: str = Form(...),
                  corners: str = Form(None)):
    frame = _decode(await image.read())
    if frame is None:
        return JSONResponse({"ok": False, "reason": "image",
                             "detail": "immagine non decodificabile"})

    det = detect.detect(frame)
    if corners:  # corner regolati a mano dall'utente: hanno priorità su YOLO
        try:
            manual = json.loads(corners)
            det["corners"] = {k: (float(v[0]), float(v[1])) for k, v in manual.items()}
        except (ValueError, TypeError, KeyError, IndexError):
            return JSONResponse({"ok": False, "reason": "corner",
                                 "detail": "corner manuali non validi"})
    res = board.build_fen(det, white_side, turn)

    # Renderizza la board 2D ogni volta che c'è una griglia, anche se la posizione
    # non è valida o l'engine non è disponibile.
    board_payload = None
    if res.get("grid") is not None:
        png = graphics.render_scacchiera(res["grid"])      # BGR ndarray, griglia orientata
        enc_ok, buf = cv2.imencode(".png", png)
        board_payload = {"grid": res["grid"],
                         "png_b64": base64.b64encode(buf.tobytes()).decode() if enc_ok else ""}

    if not res["ok"]:   # es. 'corner' (no griglia) o 'fen' (griglia sì, ma posizione invalida)
        out = {"ok": False, "reason": res["reason"], "detail": res.get("detail")}
        if board_payload:
            out["board"] = board_payload
        return JSONResponse(out)

    try:
        ev = engine.analyze(res["fen"])
    except engine.EngineUnavailable as e:
        return JSONResponse({"ok": False, "reason": "engine", "detail": str(e),
                             "fen": res["fen"], "board": board_payload})
    except (engine.IllegalPosition, ValueError) as e:  # posizione non legale
        return JSONResponse({"ok": False, "reason": "fen", "detail": str(e),
                             "fen": res["fen"], "board": board_payload})

    rc = board.uci_to_rc(ev["bestmove"]) if ev.get("bestmove") else None
    return JSONResponse({
        "ok": True,
        "fen": res["fen"],
        "eval": {"cp": ev["cp"], "mate": ev["mate"]},
        "bestmove": {"uci": ev["bestmove"], **(rc or {})},
        "board": board_payload,
    })
