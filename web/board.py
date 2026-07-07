"""Griglia 8x8 rilevata -> FEN. Funzioni pure, testabili in isolamento."""
import os
import sys

import numpy as np

_SRC = os.path.join(os.path.dirname(__file__), "..", "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)
import mapping  # noqa: E402  (modulo esistente in src/)

CORNER_NAMES = ["L-corner", "star-corner", "square-corner", "triangle-corner"]

# rotazioni np.rot90 (CCW) che portano il lato del Bianco in basso (rank1).
# left (colonna c=0) -> bottom con k=1 ; right (c=7) -> bottom con k=3 ; top -> 180.
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
        return {"ok": False, "reason": "fen", "grid": o,
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
