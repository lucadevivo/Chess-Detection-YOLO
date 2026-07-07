import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from vision import applica_euristica_re_regina  # noqa: E402


def test_lone_queen_no_king_becomes_king():
    pz = [{"classe": "white-queen", "conf": 0.9}]
    applica_euristica_re_regina(pz)
    assert pz[0]["classe"] == "white-king"


def test_two_queens_no_king_highest_conf_becomes_king():
    pz = [{"classe": "black-queen", "conf": 0.9}, {"classe": "black-queen", "conf": 0.4}]
    applica_euristica_re_regina(pz)
    assert sorted(p["classe"] for p in pz) == ["black-king", "black-queen"]
    # la regina più probabile (conf più alta) diventa il re
    assert next(p for p in pz if p["conf"] == 0.9)["classe"] == "black-king"
    assert next(p for p in pz if p["conf"] == 0.4)["classe"] == "black-queen"


def test_king_and_queen_untouched():
    pz = [{"classe": "white-king", "conf": 0.9}, {"classe": "white-queen", "conf": 0.8}]
    applica_euristica_re_regina(pz)
    assert sorted(p["classe"] for p in pz) == ["white-king", "white-queen"]


def test_two_kings_extra_becomes_queen():
    # due re dello stesso colore (impossibile): resta il piu' probabile, l'altro -> regina
    pz = [{"classe": "white-king", "conf": 0.5}, {"classe": "white-king", "conf": 0.95}]
    applica_euristica_re_regina(pz)
    assert next(p for p in pz if p["conf"] == 0.95)["classe"] == "white-king"
    assert next(p for p in pz if p["conf"] == 0.5)["classe"] == "white-queen"


def test_two_kings_with_queen_present():
    # 2 re + 1 regina: il re extra diventa regina -> 1 re, 2 regine (tutto legale)
    pz = [
        {"classe": "black-king", "conf": 0.9},
        {"classe": "black-king", "conf": 0.4},
        {"classe": "black-queen", "conf": 0.8},
    ]
    applica_euristica_re_regina(pz)
    kings = [p for p in pz if p["classe"] == "black-king"]
    queens = [p for p in pz if p["classe"] == "black-queen"]
    assert len(kings) == 1 and kings[0]["conf"] == 0.9
    assert len(queens) == 2
