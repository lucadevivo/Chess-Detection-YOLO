#!/usr/bin/env python
"""
Crop ingranditi dei PEZZI (no corner) per verifica tipo/colore.
Un foglio per frame: out/crops/<frame>.jpg, ogni crop captionato con
"#idx classe" dove idx = numero riga nel .txt (per correggere facile).
"""
import json
from pathlib import Path
import cv2, numpy as np

OUT = Path(__file__).resolve().parent / "out"
CORNER_IDS = {0, 7, 8, 9}          # L/square/star/triangle-corner
CROP_H = 180                        # altezza crop normalizzata
COLS = 5
PAD = 0.15                          # padding attorno al box


def main():
    labelmap = json.loads((OUT / "labelmap.json").read_text())
    crops_dir = OUT / "crops"
    if crops_dir.exists():
        import shutil; shutil.rmtree(crops_dir)
    crops_dir.mkdir(parents=True)

    for txt in sorted((OUT / "labels").glob("*.jpg.txt")) or sorted((OUT / "labels").glob("*.txt")):
        stem = txt.stem
        img = cv2.imread(str(OUT / "frames" / f"{stem}.jpg"))
        if img is None:
            continue
        H, W = img.shape[:2]
        tiles = []
        for idx, line in enumerate(txt.read_text().splitlines()):
            if not line.strip():
                continue
            cid, cx, cy, bw, bh = line.split()
            cid = int(cid)
            if cid in CORNER_IDS:
                continue
            cx, cy, bw, bh = float(cx), float(cy), float(bw), float(bh)
            x1 = int((cx - bw / 2 - bw * PAD) * W); x2 = int((cx + bw / 2 + bw * PAD) * W)
            y1 = int((cy - bh / 2 - bh * PAD) * H); y2 = int((cy + bh / 2 + bh * PAD) * H)
            x1, y1 = max(0, x1), max(0, y1); x2, y2 = min(W, x2), min(H, y2)
            crop = img[y1:y2, x1:x2]
            if crop.size == 0:
                continue
            scale = CROP_H / crop.shape[0]
            crop = cv2.resize(crop, (int(crop.shape[1] * scale), CROP_H))
            crop = cv2.copyMakeBorder(crop, 30, 4, 4, 4, cv2.BORDER_CONSTANT, value=(0, 0, 0))
            cv2.putText(crop, f"#{idx} {labelmap[str(cid)]}", (4, 22),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 1, cv2.LINE_AA)
            tiles.append(crop)

        if not tiles:
            continue
        maxw = max(t.shape[1] for t in tiles)
        tiles = [cv2.copyMakeBorder(t, 0, 0, 0, maxw - t.shape[1], cv2.BORDER_CONSTANT, value=(40, 40, 40)) for t in tiles]
        while len(tiles) % COLS:
            tiles.append(np.full_like(tiles[0], 40))
        rows = [np.hstack(tiles[i:i + COLS]) for i in range(0, len(tiles), COLS)]
        sheet = np.vstack(rows)
        cv2.imwrite(str(crops_dir / f"{stem}.jpg"), sheet)
        print(f"{stem}: {len([1 for l in txt.read_text().splitlines() if l.strip() and int(l.split()[0]) not in CORNER_IDS])} pezzi")


if __name__ == "__main__":
    main()
