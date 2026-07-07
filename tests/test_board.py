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


def test_build_fen_missing_corners():
    det = {"pieces": [], "corners": {"L-corner": (0, 0)}}  # <4 corner
    res = board.build_fen(det, "bottom", "w")
    assert res["ok"] is False
    assert res["reason"] == "corner"
