"""FastAPI: serve il frontend e l'endpoint /analyze."""
import base64
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


@app.post("/analyze")
async def analyze(image: UploadFile = File(...),
                  white_side: str = Form(...),
                  turn: str = Form(...)):
    raw = await image.read()
    arr = np.frombuffer(raw, np.uint8)
    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if frame is None:
        return JSONResponse({"ok": False, "reason": "image",
                             "detail": "immagine non decodificabile"})

    det = detect.detect(frame)
    res = board.build_fen(det, white_side, turn)
    if not res["ok"]:
        return JSONResponse(res)

    try:
        ev = engine.analyze(res["fen"])
    except engine.EngineUnavailable as e:
        return JSONResponse({"ok": False, "reason": "engine", "detail": str(e)})
    except Exception as e:  # FEN accettata da noi ma illegale per l'engine
        return JSONResponse({"ok": False, "reason": "fen", "detail": str(e)})

    png = graphics.render_scacchiera(res["grid"])          # BGR ndarray, griglia orientata
    ok, buf = cv2.imencode(".png", png)
    png_b64 = base64.b64encode(buf.tobytes()).decode() if ok else ""

    rc = board.uci_to_rc(ev["bestmove"]) if ev.get("bestmove") else None
    return JSONResponse({
        "ok": True,
        "fen": res["fen"],
        "eval": {"cp": ev["cp"], "mate": ev["mate"]},
        "bestmove": {"uci": ev["bestmove"], **(rc or {})},
        "board": {"grid": res["grid"], "png_b64": png_b64},
    })
