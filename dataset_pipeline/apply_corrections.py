#!/usr/bin/env python
"""Applica le correzioni della review di Claude ai .txt YOLO in out/labels."""
import shutil
from pathlib import Path

OUT = Path(__file__).resolve().parent / "out"

# idx = numero riga nel .txt (== #idx nei crop). name->id da labelmap.
RELABEL = {   # frame: {idx: nuovo_class_id}
    "clip_132238_0001": {1: 13},   # white-rook -> white-pawn
    "clip_132238_0011": {0: 13},   # white-rook -> white-pawn
    "clip_132311_0003": {5: 6},    # black-knight -> black-rook
}
DELETE = {    # frame: [idx da rimuovere]
    "clip_132238_0005": [10],
    "clip_132238_0012": [8],
    "clip_132429_0001": [13],
    "clip_132512_0011": [10],
    "clip_132531_0004": [2, 12, 13],
    "clip_132605_0010": [8],
    "clip_132605_0011": [8],
    "clip_132605_0013": [11],
    "clip_132627_0001": [10],
    "clip_132824_0008": [15],
}
DROP_FRAME = ["clip_132605_0009"]


def lines_of(txt):
    return [l for l in txt.read_text().splitlines() if l.strip()]


def main():
    # 1) drop interi frame -> _dropped/
    dropped = OUT / "_dropped"
    for sub in ("frames", "labels", "preview", "crops"):
        (dropped / sub).mkdir(parents=True, exist_ok=True)
    for stem in DROP_FRAME:
        for sub, ext in (("frames", ".jpg"), ("labels", ".txt"), ("preview", ".jpg"), ("crops", ".jpg")):
            p = OUT / sub / f"{stem}{ext}"
            if p.exists():
                shutil.move(str(p), dropped / sub / p.name)
        print(f"drop frame {stem}")

    # 2) relabel
    for stem, changes in RELABEL.items():
        txt = OUT / "labels" / f"{stem}.txt"
        lines = lines_of(txt)
        for idx, new_id in changes.items():
            parts = lines[idx].split()
            old = parts[0]; parts[0] = str(new_id)
            lines[idx] = " ".join(parts)
            print(f"relabel {stem} #{idx}: {old} -> {new_id}")
        txt.write_text("\n".join(lines))

    # 3) delete (indici in ordine decrescente per non sfasare)
    for stem, idxs in DELETE.items():
        txt = OUT / "labels" / f"{stem}.txt"
        lines = lines_of(txt)
        for idx in sorted(idxs, reverse=True):
            removed = lines.pop(idx)
            print(f"delete {stem} #{idx}: {removed.split()[0]}")
        txt.write_text("\n".join(lines))

    print("\nfatto. Correzioni applicate ai .txt.")


if __name__ == "__main__":
    main()
