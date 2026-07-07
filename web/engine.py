"""Wrapper Stockfish via python-chess."""
import os
import shutil

import chess
import chess.engine

DEFAULT_MOVETIME = 1.0       # secondi
# su Debian il pacchetto installa /usr/games/stockfish (non nel PATH di default)
_CANDIDATES = ("stockfish", "/usr/games/stockfish", "/usr/local/bin/stockfish")


class EngineUnavailable(RuntimeError):
    pass


class IllegalPosition(ValueError):
    """Posizione non legale: NON passarla a Stockfish (va in segfault)."""
    pass


def _find_stockfish():
    for cand in _CANDIDATES:
        p = shutil.which(cand) if os.sep not in cand else (cand if os.path.exists(cand) else None)
        if p:
            return p
    return None


def analyze(fen, movetime=DEFAULT_MOVETIME):
    """FEN -> {cp, mate, bestmove}. cp/mate dal punto di vista del Bianco."""
    board = chess.Board(fen)  # solleva ValueError se FEN malformata
    # Stockfish segfaulta su posizioni illegali (es. lato non di turno sotto scacco):
    # filtrarle PRIMA di spawnare l'engine.
    if not board.is_valid():
        raise IllegalPosition(f"posizione non legale ({board.status()!r})")
    binary = _find_stockfish()
    if binary is None:
        raise EngineUnavailable("binario 'stockfish' non trovato")
    limit = chess.engine.Limit(time=movetime)
    with chess.engine.SimpleEngine.popen_uci(binary) as eng:
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
