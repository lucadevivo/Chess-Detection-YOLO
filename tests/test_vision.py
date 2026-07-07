import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from vision import applica_euristica_re_regina  # noqa: E402


def test_lone_queen_no_king_becomes_king():
    pz = [{"classe": "white-queen", "conf": 0.9}]
    applica_euristica_re_regina(pz)
    assert pz[0]["classe"] == "white-king"


def test_two_queens_no_king_lowest_conf_becomes_king():
    pz = [{"classe": "black-queen", "conf": 0.9}, {"classe": "black-queen", "conf": 0.4}]
    applica_euristica_re_regina(pz)
    assert sorted(p["classe"] for p in pz) == ["black-king", "black-queen"]
    # la regina a conf più alta resta regina
    assert next(p for p in pz if p["conf"] == 0.9)["classe"] == "black-queen"


def test_king_and_queen_untouched():
    pz = [{"classe": "white-king", "conf": 0.9}, {"classe": "white-queen", "conf": 0.8}]
    applica_euristica_re_regina(pz)
    assert sorted(p["classe"] for p in pz) == ["white-king", "white-queen"]
