#!/usr/bin/env python
"""
Dedup perceptual: scarta frame quasi-identici (board ferma a 1fps).
Sposta scarti in out/_dups/ (nulla perso). Downstream vede solo i survivor.

    python dataset_pipeline/dedup.py [soglia_hamming]   # default 8
"""
import sys, shutil
from pathlib import Path
import cv2, numpy as np

OUT = Path(__file__).resolve().parent / "out"
THRESH = int(sys.argv[1]) if len(sys.argv) > 1 else 8


def ahash(img_path, s=8):
    g = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
    g = cv2.resize(g, (s, s), interpolation=cv2.INTER_AREA)
    return (g > g.mean()).flatten()


def main():
    frames = sorted((OUT / "frames").glob("*.jpg"))
    kept, hashes = [], []
    for f in frames:
        h = ahash(f)
        if all(np.count_nonzero(h != k) > THRESH for k in hashes):
            kept.append(f); hashes.append(h)

    dups = OUT / "_dups"
    for sub in ("frames", "labels", "preview"):
        (dups / sub).mkdir(parents=True, exist_ok=True)
    keep_names = {f.stem for f in kept}
    moved = 0
    for f in frames:
        if f.stem in keep_names:
            continue
        shutil.move(str(f), dups / "frames" / f.name)
        for sub, ext in (("labels", ".txt"), ("preview", ".jpg")):
            p = OUT / sub / f"{f.stem}{ext}"
            if p.exists():
                shutil.move(str(p), dups / sub / p.name)
        moved += 1

    print(f"tenuti {len(kept)}/{len(frames)} frame (soglia {THRESH}), spostati {moved} dup in {dups}")
    for f in kept:
        print(f"  {f.name}")


if __name__ == "__main__":
    main()
