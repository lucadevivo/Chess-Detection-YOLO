import shutil

import pytest

from web import engine

stockfish_missing = shutil.which("stockfish") is None


def test_illegal_position_raises_before_engine():
    # posizione illegale (re nero sotto scacco, turno al Bianco): niente crash,
    # niente spawn engine -> gira anche senza stockfish installato.
    import pytest as _pt
    with _pt.raises(engine.IllegalPosition):
        engine.analyze("3k4/8/8/8/8/8/8/3RK3 w - - 0 1", movetime=0.5)


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
