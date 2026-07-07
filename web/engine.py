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
