# Chess Vision Web App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Trasformare l'app desktop OpenCV di riconoscimento scacchiera in una web app dockerizzata con camera picker, barra di valutazione stile chess.com e mossa migliore via Stockfish.

**Architecture:** Backend FastAPI (Docker) che riusa la logica di visione esistente (`src/vision.py`, `src/mapping.py`, `src/graphics.py`); frontend statico nel browser che legge la webcam via `getUserMedia`, cattura un frame su richiesta e lo manda a `POST /analyze`, ricevendo FEN, valutazione e mossa migliore. La webcam vive nel browser → nessun passthrough device → cross-platform.

**Tech Stack:** Python 3.12, FastAPI, uvicorn, ultralytics (YOLOv8), OpenCV (headless nel container), python-chess + Stockfish, numpy, HTML/CSS/JS vanilla, Docker.

## Global Constraints

- Python 3.12.
- Il modello YOLO è `best.pt` nella root del progetto; caricato UNA volta all'avvio del backend, mai per richiesta.
- Riusare i moduli esistenti in `src/` (`vision.rileva_elementi`, `mapping.calcola_omografia`, `mapping.proietta_pezzi`, `graphics.render_scacchiera`) senza modificarli. I moduli `web/` li importano aggiungendo `src/` a `sys.path`.
- Formato celle griglia (da `mapping.proietta_pezzi`): stringa `"wk"`, `"bp"`, ... (colore `w`/`b` + tipo `p/r/n/b/q/k`) oppure `" . "` per vuoto.
- Classi corner del modello: `L-corner`, `star-corner`, `square-corner`, `triangle-corner`.
- `white_side` ∈ {`bottom`, `top`, `left`, `right`}; `turn` ∈ {`w`, `b`}.
- Il client non riceve mai stacktrace: ogni errore gestito → JSON `{ok:false, reason, detail}`.
- Nel container si usa `opencv-python-headless` (nessuna GUI server-side).
- Nuova cartella `web/`; `src/` resta invariato (legacy desktop app).
- Commit dopo ogni task. Non fare push. Il repo NON è il vault, quindi nessun commit automatico oltre quelli previsti dal piano.

---

## File Structure

```
web/
  __init__.py          # package marker
  board.py             # griglia -> FEN, orientamento, uci<->rc  (core testabile)
  engine.py            # wrapper Stockfish (python-chess)
  detect.py            # wrapper YOLO -> {pieces, corners}
  app.py               # FastAPI: GET / , POST /analyze
  static/
    index.html
    app.js
    style.css
  requirements.txt     # dipendenze web app
tests/
  __init__.py
  test_board.py
  test_engine.py
  test_api.py
Dockerfile             # root: build context = root (serve src/ e best.pt)
.dockerignore
```

---

### Task 1: `web/board.py` — grid → FEN (core puro, testabile)

Funzioni pure per convertire una griglia 8×8 in FEN, gestire l'orientamento e mappare le mosse UCI in coordinate di griglia. Nessuna dipendenza da YOLO qui (quello arriva nel Task 3).

**Files:**
- Create: `web/__init__.py` (vuoto)
- Create: `tests/__init__.py` (vuoto)
- Create: `web/board.py`
- Test: `tests/test_board.py`

**Interfaces:**
- Produces:
  - `cell_to_fen_char(cell: str) -> str | None`
  - `orient_grid(grid: list[list[str]], white_side: str) -> list[list[str]]`
  - `grid_to_fen(grid: list[list[str]], white_side: str, turn: str) -> dict` con `{ok:True, fen:str, grid:list[list[str]]}` oppure `{ok:False, reason:str, detail:str}`
  - `uci_to_rc(uci: str) -> dict` con `{from:[r,c], to:[r,c]}` (coord nella griglia ORIENTATA: r=0 è rank8 in alto, c=0 è colonna a)

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_board.py
from web import board


def test_cell_to_fen_char():
    assert board.cell_to_fen_char("wk") == "K"
    assert board.cell_to_fen_char("bp") == "p"
    assert board.cell_to_fen_char("wq") == "Q"
    assert board.cell_to_fen_char(" . ") is None
    assert board.cell_to_fen_char("") is None
    assert board.cell_to_fen_char("xz") is None


def _empty_grid():
    return [[" . " for _ in range(8)] for _ in range(8)]


def test_orient_top_is_180():
    g = _empty_grid()
    g[0][0] = "wk"
    o = board.orient_grid(g, "top")
    assert o[7][7] == "wk"


def test_orient_bottom_is_identity():
    g = _empty_grid()
    g[3][2] = "bp"
    o = board.orient_grid(g, "bottom")
    assert o[3][2] == "bp"


def test_grid_to_fen_two_kings():
    g = _empty_grid()
    g[0][4] = "bk"   # rank8 e8 (white_side=bottom => nessuna rotazione)
    g[7][4] = "wk"   # rank1 e1
    res = board.grid_to_fen(g, "bottom", "w")
    assert res["ok"] is True
    assert res["fen"] == "4k3/8/8/8/8/8/8/4K3 w - - 0 1"


def test_grid_to_fen_missing_king():
    g = _empty_grid()
    g[7][4] = "wk"   # manca il re nero
    res = board.grid_to_fen(g, "bottom", "w")
    assert res["ok"] is False
    assert res["reason"] == "fen"


def test_grid_to_fen_extra_king_kept_one():
    g = _empty_grid()
    g[0][4] = "bk"
    g[7][4] = "wk"
    g[7][5] = "wk"   # secondo re bianco -> deve restarne uno
    res = board.grid_to_fen(g, "bottom", "w")
    assert res["ok"] is True
    assert res["fen"].split()[0].count("K") == 1


def test_grid_to_fen_pawn_on_back_rank_dropped():
    g = _empty_grid()
    g[0][4] = "bk"
    g[7][4] = "wk"
    g[0][0] = "wp"   # pedone su rank8 = errore, va scartato
    res = board.grid_to_fen(g, "bottom", "w")
    assert res["ok"] is True
    assert "P" not in res["fen"].split()[0]


def test_uci_to_rc():
    rc = board.uci_to_rc("e2e4")
    assert rc["from"] == [6, 4]   # e2: file e=4, rank2 -> row 8-2=6
    assert rc["to"] == [4, 4]     # e4: row 8-4=4
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/luca/Scrivania/AILab/AILabProject && .venv/bin/python -m pytest tests/test_board.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'web.board'`)

- [ ] **Step 3: Implement `web/board.py`**

```python
# web/board.py
"""Griglia 8x8 rilevata -> FEN. Funzioni pure, testabili in isolamento."""
import numpy as np

# rotazioni np.rot90 (CCW) che portano il lato del Bianco in basso (rank1).
# left  (colonna c=0) -> bottom con k=1 ; right (c=7) -> bottom con k=3 ; top -> 180.
_ROT = {"bottom": 0, "left": 1, "top": 2, "right": 3}


def cell_to_fen_char(cell):
    """'wk'->'K', 'bp'->'p', vuoto/invalidi -> None."""
    c = (cell or "").strip()
    if len(c) < 2:
        return None
    color, kind = c[0], c[1]
    if color not in ("w", "b") or kind not in "prnbqk":
        return None
    return kind.upper() if color == "w" else kind.lower()


def orient_grid(grid, white_side):
    """Ruota la griglia così che il lato del Bianco sia in basso (rank1)."""
    if white_side not in _ROT:
        raise ValueError(f"white_side non valido: {white_side}")
    g = np.array(grid, dtype=object)
    return np.rot90(g, _ROT[white_side]).tolist()


def _dedup_kings(grid):
    """Tiene un solo re per colore (il primo trovato), svuota gli altri."""
    seen = {"K": False, "k": False}
    for r in range(8):
        for c in range(8):
            ch = cell_to_fen_char(grid[r][c])
            if ch in ("K", "k"):
                if seen[ch]:
                    grid[r][c] = " . "
                else:
                    seen[ch] = True
    return seen


def grid_to_fen(grid, white_side, turn):
    """griglia camera-frame -> {ok, fen, grid(orientata)} | {ok:False, reason, detail}."""
    if turn not in ("w", "b"):
        return {"ok": False, "reason": "fen", "detail": "turno non valido"}
    o = orient_grid(grid, white_side)   # o[0]=rank8 (alto), o[7]=rank1 (basso)
    seen = _dedup_kings(o)
    if not seen["K"] or not seen["k"]:
        return {"ok": False, "reason": "fen",
                "detail": f"re mancante (bianco={seen['K']}, nero={seen['k']})"}
    ranks = []
    for r in range(8):
        empty = 0
        s = ""
        for c in range(8):
            ch = cell_to_fen_char(o[r][c])
            if ch in ("p", "P") and r in (0, 7):   # pedone su rank1/8 = errore
                ch = None
            if ch is None:
                empty += 1
            else:
                if empty:
                    s += str(empty)
                    empty = 0
                s += ch
        if empty:
            s += str(empty)
        ranks.append(s)
    fen = "/".join(ranks) + f" {turn} - - 0 1"
    return {"ok": True, "fen": fen, "grid": o}


def uci_to_rc(uci):
    """'e2e4' -> {from:[r,c], to:[r,c]} nella griglia orientata (r0=rank8, c0=col a)."""
    def sq(s):
        file = ord(s[0]) - ord("a")
        rank = int(s[1])
        return [8 - rank, file]
    return {"from": sq(uci[0:2]), "to": sq(uci[2:4])}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_board.py -v`
Expected: PASS (8 test)

- [ ] **Step 5: Commit**

```bash
git add web/__init__.py web/board.py tests/__init__.py tests/test_board.py
git commit -m "feat(web): board grid->FEN, orientamento e uci->rc con test"
```

---

### Task 2: `web/board.py` — `build_fen` da rilevamento (omografia)

Aggiunge la funzione che parte dal rilevamento (pezzi + corner) e produce la FEN, usando l'omografia esistente di `mapping.py`.

**Files:**
- Modify: `web/board.py` (aggiunge import di `mapping` via sys.path e `build_fen`)
- Test: `tests/test_board.py` (aggiunge un test)

**Interfaces:**
- Consumes: `mapping.calcola_omografia(angoli) -> M`, `mapping.proietta_pezzi(pezzi, M) -> grid`, `grid_to_fen` (Task 1)
- Produces: `build_fen(detection: dict, white_side: str, turn: str) -> dict` dove `detection = {"pieces":[...], "corners":{nome:(x,y)}}`; ritorna come `grid_to_fen`, oppure `{ok:False, reason:"corner", detail:...}` se mancano corner.

- [ ] **Step 1: Write the failing test**

```python
# aggiungere in tests/test_board.py
def test_build_fen_missing_corners():
    det = {"pieces": [], "corners": {"L-corner": (0, 0)}}  # <4 corner
    res = board.build_fen(det, "bottom", "w")
    assert res["ok"] is False
    assert res["reason"] == "corner"
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_board.py::test_build_fen_missing_corners -v`
Expected: FAIL (`AttributeError: module 'web.board' has no attribute 'build_fen'`)

- [ ] **Step 3: Implement `build_fen` (aggiungere in `web/board.py`)**

In cima al file, dopo `import numpy as np`, aggiungere l'import di `mapping` da `src/`:

```python
import os
import sys
_SRC = os.path.join(os.path.dirname(__file__), "..", "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)
import mapping  # noqa: E402  (modulo esistente in src/)

CORNER_NAMES = ["L-corner", "star-corner", "square-corner", "triangle-corner"]
```

In fondo al file, aggiungere:

```python
def build_fen(detection, white_side, turn):
    """detection {pieces, corners} -> FEN. Errore 'corner' se mancano i 4 marker."""
    corners = detection.get("corners", {})
    if not all(name in corners for name in CORNER_NAMES):
        return {"ok": False, "reason": "corner",
                "detail": "servono tutti e 4 i marker d'angolo"}
    try:
        M = mapping.calcola_omografia(corners)
        grid = mapping.proietta_pezzi(detection.get("pieces", []), M)
    except Exception as e:  # omografia degenere / matrice non invertibile
        return {"ok": False, "reason": "corner", "detail": f"omografia fallita: {e}"}
    return grid_to_fen(grid, white_side, turn)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_board.py -v`
Expected: PASS (9 test)

- [ ] **Step 5: Commit**

```bash
git add web/board.py tests/test_board.py
git commit -m "feat(web): build_fen da rilevamento via omografia esistente"
```

---

### Task 3: `web/engine.py` — wrapper Stockfish

**Files:**
- Create: `web/engine.py`
- Test: `tests/test_engine.py`

**Interfaces:**
- Produces: `analyze(fen: str, movetime: float = 1.0) -> dict` con `{cp:int|None, mate:int|None, bestmove:str}` (cp dal punto di vista del Bianco). Solleva `EngineUnavailable` se il binario manca.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_engine.py
import shutil
import pytest
from web import engine

stockfish_missing = shutil.which("stockfish") is None


@pytest.mark.skipif(stockfish_missing, reason="binario stockfish non installato")
def test_mate_in_one():
    # Bianco muove e matta: Rb1-b8#
    fen = "6k1/8/6K1/8/8/8/8/1R6 w - - 0 1"
    res = engine.analyze(fen, movetime=0.5)
    assert res["mate"] == 1
    assert res["bestmove"].startswith("b1b8")


@pytest.mark.skipif(stockfish_missing, reason="binario stockfish non installato")
def test_startpos_returns_legal_move():
    import chess
    fen = chess.STARTING_FEN
    res = engine.analyze(fen, movetime=0.5)
    board_ = chess.Board(fen)
    assert chess.Move.from_uci(res["bestmove"]) in board_.legal_moves
    assert isinstance(res["cp"], int)
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_engine.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'web.engine'`). Se stockfish non è installato in locale: `sudo pacman -S stockfish` (Arch) per eseguire i test; in Docker è incluso.

- [ ] **Step 3: Implement `web/engine.py`**

```python
# web/engine.py
"""Wrapper Stockfish via python-chess."""
import shutil
import chess
import chess.engine

STOCKFISH = "stockfish"      # binario nel PATH
DEFAULT_MOVETIME = 1.0       # secondi


class EngineUnavailable(RuntimeError):
    pass


def analyze(fen, movetime=DEFAULT_MOVETIME):
    """FEN -> {cp, mate, bestmove}. cp/mate dal punto di vista del Bianco."""
    if shutil.which(STOCKFISH) is None:
        raise EngineUnavailable("binario 'stockfish' non trovato nel PATH")
    board = chess.Board(fen)  # solleva ValueError se FEN malformata
    limit = chess.engine.Limit(time=movetime)
    with chess.engine.SimpleEngine.popen_uci(STOCKFISH) as eng:
        info = eng.analyse(board, limit)
        score = info["score"].white()
        best = eng.play(board, limit).move
    return {
        "cp": score.score(),        # None se matto
        "mate": score.mate(),       # None se non matto; segno = chi matta
        "bestmove": best.uci() if best else None,
    }


if __name__ == "__main__":  # self-check
    r = analyze("6k1/8/6K1/8/8/8/8/1R6 w - - 0 1", movetime=0.5)
    assert r["mate"] == 1, r
    print("engine self-check OK:", r)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_engine.py -v`
Expected: PASS (2 test), oppure SKIPPED se stockfish non installato in locale.

- [ ] **Step 5: Commit**

```bash
git add web/engine.py tests/test_engine.py
git commit -m "feat(web): wrapper Stockfish con eval+bestmove"
```

---

### Task 4: `web/detect.py` — wrapper YOLO

**Files:**
- Create: `web/detect.py`

**Interfaces:**
- Consumes: `vision.rileva_elementi(frame, model) -> (angoli, pezzi)` (esistente in `src/`)
- Produces:
  - `load_model(path: str) -> model` (memorizza il modello a livello di modulo)
  - `detect(frame_bgr, model=None) -> dict` = `{"pieces":[{classe,punto_reale,conf}], "corners":{nome:(x,y)}}`

- [ ] **Step 1: Implement `web/detect.py`**

(Questo task non ha un unit test dedicato: dipende dal modello reale e dalla webcam; è coperto dallo smoke test API del Task 5.)

```python
# web/detect.py
"""Wrapper del rilevamento YOLO esistente (src/vision.py)."""
import os
import sys

_SRC = os.path.join(os.path.dirname(__file__), "..", "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from ultralytics import YOLO  # noqa: E402
import vision                 # noqa: E402  (modulo esistente in src/)

_model = None


def load_model(path):
    """Carica il modello YOLO una volta e lo memorizza."""
    global _model
    _model = YOLO(path)
    return _model


def detect(frame_bgr, model=None):
    """frame BGR -> {pieces, corners} usando la logica esistente."""
    m = model or _model
    if m is None:
        raise RuntimeError("modello non caricato: chiama load_model() prima")
    angoli, pezzi = vision.rileva_elementi(frame_bgr, m)
    return {"pieces": pezzi, "corners": angoli}
```

- [ ] **Step 2: Smoke check manuale (import)**

Run: `.venv/bin/python -c "from web import detect; print('import ok')"`
Expected: stampa `import ok` (nessun errore di import).

- [ ] **Step 3: Commit**

```bash
git add web/detect.py
git commit -m "feat(web): wrapper detect YOLO -> pieces+corners"
```

---

### Task 5: `web/app.py` — FastAPI + smoke test

**Files:**
- Create: `web/app.py`
- Create: `web/requirements.txt`
- Test: `tests/test_api.py`

**Interfaces:**
- Consumes: `detect.load_model`, `detect.detect`, `board.build_fen`, `board.uci_to_rc`, `engine.analyze`, `graphics.render_scacchiera`
- Produces: app FastAPI con `GET /` (serve `index.html`) e `POST /analyze` (multipart: `image`, `white_side`, `turn`) → JSON come da spec.

- [ ] **Step 1: Write `web/requirements.txt`**

```text
fastapi
uvicorn[standard]
python-multipart
ultralytics
opencv-python-headless
python-chess
numpy
```

(torch viene tirato da ultralytics; nel Dockerfile si forza la versione CPU.)

- [ ] **Step 2: Write the failing smoke test**

```python
# tests/test_api.py
import io
import os
import shutil
import numpy as np
import cv2
import pytest
from fastapi.testclient import TestClient

MODEL = os.path.join(os.path.dirname(__file__), "..", "best.pt")
missing = (not os.path.exists(MODEL)) or (shutil.which("stockfish") is None)


@pytest.mark.skipif(missing, reason="serve best.pt + stockfish")
def test_analyze_no_board_returns_corner_reason():
    from web.app import app
    client = TestClient(app)
    # frame bianco senza scacchiera: niente corner -> reason 'corner'
    blank = np.full((480, 640, 3), 255, np.uint8)
    ok, buf = cv2.imencode(".jpg", blank)
    files = {"image": ("f.jpg", io.BytesIO(buf.tobytes()), "image/jpeg")}
    data = {"white_side": "bottom", "turn": "w"}
    r = client.post("/analyze", files=files, data=data)
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is False
    assert body["reason"] == "corner"
```

- [ ] **Step 3: Run to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_api.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'web.app'`) o SKIPPED se mancano `best.pt`/stockfish.

- [ ] **Step 4: Implement `web/app.py`**

```python
# web/app.py
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
```

- [ ] **Step 5: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_api.py -v`
Expected: PASS (o SKIPPED se mancano `best.pt`/stockfish).

- [ ] **Step 6: Commit**

```bash
git add web/app.py web/requirements.txt tests/test_api.py
git commit -m "feat(web): endpoint FastAPI /analyze + smoke test"
```

---

### Task 6: Frontend statico (camera picker, barra eval, board, freccia)

**Files:**
- Create: `web/static/index.html`
- Create: `web/static/style.css`
- Create: `web/static/app.js`

**Interfaces:**
- Consumes: `GET /` , `POST /analyze` (multipart) → JSON del Task 5.
- Produces: UI completa. Nessun unit test automatico (verifica manuale nel Task 7).

- [ ] **Step 1: Write `web/static/index.html`**

```html
<!doctype html>
<html lang="it">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Chess Vision</title>
  <link rel="stylesheet" href="/static/style.css">
</head>
<body>
  <h1>Chess Vision</h1>
  <div class="row">
    <div class="col">
      <video id="preview" autoplay playsinline muted></video>
      <div class="controls">
        <label>Fotocamera
          <select id="camera"></select>
        </label>
        <label>Bianco gioca da
          <select id="white_side">
            <option value="bottom">in basso</option>
            <option value="top">in alto</option>
            <option value="left">sinistra</option>
            <option value="right">destra</option>
          </select>
        </label>
        <label>Turno
          <select id="turn">
            <option value="w">Bianco</option>
            <option value="b">Nero</option>
          </select>
        </label>
        <button id="analyze">Analizza</button>
      </div>
      <p id="status"></p>
    </div>
    <div class="col">
      <div class="eval-wrap">
        <div class="eval-bar"><div id="eval-white"></div></div>
        <span id="eval-label">—</span>
      </div>
      <div class="board-wrap">
        <img id="board" alt="board">
        <canvas id="arrow"></canvas>
      </div>
      <p id="bestmove"></p>
    </div>
  </div>
  <canvas id="capture" hidden></canvas>
  <script src="/static/app.js"></script>
</body>
</html>
```

- [ ] **Step 2: Write `web/static/style.css`**

```css
* { box-sizing: border-box; }
body { font-family: system-ui, sans-serif; margin: 1rem; background:#111; color:#eee; }
h1 { font-size: 1.3rem; }
.row { display:flex; gap:1.5rem; flex-wrap:wrap; }
.col { flex:1; min-width:320px; }
video { width:100%; max-width:480px; border-radius:8px; background:#000; }
.controls { display:flex; flex-direction:column; gap:.5rem; margin-top:.5rem; max-width:480px; }
.controls label { display:flex; justify-content:space-between; align-items:center; gap:.5rem; }
select, button { padding:.4rem; border-radius:6px; }
button { background:#3a7; color:#fff; border:0; cursor:pointer; font-weight:600; }
button:disabled { opacity:.5; cursor:default; }
.eval-wrap { display:flex; align-items:center; gap:.75rem; margin-bottom:1rem; }
.eval-bar { position:relative; width:36px; height:360px; background:#222; border-radius:6px; overflow:hidden; display:flex; flex-direction:column-reverse; }
#eval-white { width:100%; background:#f5f5f5; height:50%; transition:height .3s; }
#eval-label { font-variant-numeric:tabular-nums; font-weight:700; }
.board-wrap { position:relative; width:360px; max-width:100%; }
#board { width:100%; display:block; border-radius:6px; }
#arrow { position:absolute; inset:0; width:100%; height:100%; pointer-events:none; }
#status { color:#f88; min-height:1.2em; }
```

- [ ] **Step 3: Write `web/static/app.js`**

```javascript
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
  $("eval-white").style.height = pct + "%";
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
    if (!body.ok) {
      const msg = { corner: "Riquadra bene la scacchiera (4 marker).",
                    fen: "Posizione non valida: " + (body.detail || ""),
                    engine: "Motore non disponibile: " + (body.detail || ""),
                    image: "Immagine non valida." };
      $("status").textContent = msg[body.reason] || body.detail || "Errore.";
      return;
    }
    $("status").textContent = "";
    $("board").src = "data:image/png;base64," + body.board.png_b64;
    $("board").onload = () => drawArrow(body.bestmove);
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
```

- [ ] **Step 4: Commit**

```bash
git add web/static/index.html web/static/style.css web/static/app.js
git commit -m "feat(web): frontend camera picker, barra eval, board e freccia"
```

---

### Task 7: Docker + verifica end-to-end + README

**Files:**
- Create: `Dockerfile` (root)
- Create: `.dockerignore`
- Modify: `README.md` (sezione "Web app")

**Interfaces:** nessuna nuova API. Deliverable: immagine Docker che serve la web app.

- [ ] **Step 1: Write `.dockerignore`**

```text
.venv
dataset_pipeline/out
dataset_pipeline/_dups
dataset_pipeline/videos
dataset_pipeline/*.mp4
**/__pycache__
runs
*.mp4
docs
```

- [ ] **Step 2: Write `Dockerfile` (root)**

```dockerfile
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        stockfish libgl1 libglib2.0-0 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# torch CPU-only prima (evita il wheel CUDA gigante)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

COPY web/requirements.txt /app/web/requirements.txt
RUN pip install --no-cache-dir -r /app/web/requirements.txt

COPY src/ /app/src/
COPY web/ /app/web/
COPY best.pt /app/best.pt

EXPOSE 8000
CMD ["uvicorn", "web.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 3: Build dell'immagine**

Run: `cd /home/luca/Scrivania/AILab/AILabProject && docker build -t chess-vision .`
Expected: build completa senza errori, immagine `chess-vision` creata.

- [ ] **Step 4: Avvio e verifica end-to-end**

Run: `docker run --rm -p 8000:8000 chess-vision`
Poi nel browser: `http://localhost:8000`
Verifica manuale:
- Il selettore fotocamera appare se ci sono più webcam; la preview mostra il video.
- Con la scacchiera inquadrata, scegli lato Bianco + turno, premi **Analizza**.
- Compaiono: board 2D, barra eval (bianco/nero secondo il vantaggio), freccia mossa migliore.
- Senza scacchiera inquadrata → messaggio "Riquadra bene la scacchiera".

- [ ] **Step 5: Aggiorna `README.md`**

Aggiungere in fondo al README:

```markdown
## Web app (Docker)

Riconoscimento + valutazione stile chess.com nel browser.

```bash
docker build -t chess-vision .
docker run --rm -p 8000:8000 chess-vision
# apri http://localhost:8000
```

La webcam viene letta dal browser (getUserMedia), quindi funziona su Linux/Mac/Windows
senza passthrough di device. Scegli la fotocamera, il lato del Bianco e il turno, poi
premi "Analizza": ottieni la posizione rilevata, la barra di valutazione e la mossa
migliore (Stockfish).
```

- [ ] **Step 6: Commit**

```bash
git add Dockerfile .dockerignore README.md
git commit -m "feat(web): Dockerfile, dockerignore e README web app"
```

---

## Self-Review

**Spec coverage:**
- Camera picker → Task 6 (`listCameras`). ✓
- Barra eval + mossa migliore → Task 5 (endpoint) + Task 6 (barra, freccia). ✓
- Utente specifica turno + lato Bianco → Task 6 (select) → Task 1/2 (FEN). ✓
- Dockerizzazione cross-platform → Task 7. ✓
- Riuso `src/` senza modifiche → Task 2/4/5 via sys.path. ✓
- Gestione errori JSON `{ok:false}` → Task 5 (corner/fen/engine/image). ✓
- Testing (board/engine/api) → Task 1/2/3/5. ✓

**Placeholder scan:** nessun TBD/TODO; ogni step ha codice o comando reale.

**Type consistency:**
- `build_fen`/`grid_to_fen` ritornano sempre dict con `ok` (+`fen`,`grid` | `reason`,`detail`) — coerente tra Task 1, 2, 5.
- `detect.detect` → `{pieces, corners}` consumato da `build_fen` (`corners` dict, `pieces` list). ✓
- `engine.analyze` → `{cp, mate, bestmove}` consumato da Task 5; `uci_to_rc` → `{from,to}` unito in `bestmove` per il frontend, che legge `bestmove.from/to/uci`. ✓
- Griglia orientata (`res["grid"]`) passata sia a `render_scacchiera` sia usata come riferimento per `uci_to_rc` (stesso frame orientato, r0=rank8). ✓
