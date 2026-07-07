#!/usr/bin/env python
"""Contact-sheet delle preview per triage veloce. out/sheets/sheet_NN.jpg"""
from pathlib import Path
import cv2, numpy as np

OUT = Path(__file__).resolve().parent / "out"
PER = 6          # 2 col x 3 righe
COLS = 2

def main():
    prevs = sorted((OUT / "preview").glob("*.jpg"))
    sheets = OUT / "sheets"
    if sheets.exists():
        import shutil; shutil.rmtree(sheets)
    sheets.mkdir(parents=True)
    for s in range(0, len(prevs), PER):
        batch = prevs[s:s + PER]
        tiles = []
        for p in batch:
            img = cv2.imread(str(p))
            # banner col nome file in alto
            band = np.zeros((26, img.shape[1], 3), np.uint8)
            cv2.putText(band, p.stem, (6, 19), cv2.FONT_HERSHEY_SIMPLEX,
                        0.6, (0, 255, 255), 2, cv2.LINE_AA)
            tiles.append(np.vstack([band, img]))
        # pad ultimo gruppo
        while len(tiles) < PER:
            tiles.append(np.zeros_like(tiles[0]))
        rows = [np.hstack(tiles[i:i + COLS]) for i in range(0, PER, COLS)]
        sheet = np.vstack(rows)
        n = s // PER + 1
        cv2.imwrite(str(sheets / f"sheet_{n:02d}.jpg"), sheet)
        print(f"sheet_{n:02d}.jpg  ({len(batch)} frame)")

if __name__ == "__main__":
    main()
