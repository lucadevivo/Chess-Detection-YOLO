#!/usr/bin/env python
"""
Registratore webcam con anteprima live. Salva in dataset_pipeline/videos/.

    python dataset_pipeline/record.py            # LifeCam (/dev/video2)
    python dataset_pipeline/record.py 0          # altra camera

Tasti nella finestra:
    SPAZIO = avvia / ferma registrazione (puoi fare piu' clip)
    Q      = esci
Consiglio: registra clip corti (30-60s) variando angolo/luce/posizione pezzi.
"""
import sys, cv2, datetime
from pathlib import Path

SORGENTE = int(sys.argv[1]) if len(sys.argv) > 1 else 2
VIDEOS = Path(__file__).resolve().parent / "videos"
VIDEOS.mkdir(exist_ok=True)

cap = cv2.VideoCapture(SORGENTE)
if not cap.isOpened():
    print(f"camera {SORGENTE} non apre"); sys.exit(1)

fps = cap.get(cv2.CAP_PROP_FPS) or 20.0
w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
fourcc = cv2.VideoWriter_fourcc(*"mp4v")

writer = None
n_clip = 0
print("SPAZIO=rec on/off, Q=esci")

while True:
    ok, frame = cap.read()
    if not ok:
        print("frame perso"); break

    if writer is not None:
        writer.write(frame)

    view = frame.copy()
    rec = writer is not None
    cv2.putText(view, "REC" if rec else "PRONTO (SPAZIO per registrare)",
                (15, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                (0, 0, 255) if rec else (0, 255, 0), 2, cv2.LINE_AA)
    if rec:
        cv2.circle(view, (w - 30, 30), 12, (0, 0, 255), -1)
    cv2.imshow("Record - SPAZIO rec, Q esci", view)

    key = cv2.waitKey(1) & 0xFF
    if key == ord(' '):
        if writer is None:
            n_clip += 1
            ts = datetime.datetime.now().strftime("%H%M%S")
            path = VIDEOS / f"clip_{ts}.mp4"
            writer = cv2.VideoWriter(str(path), fourcc, fps, (w, h))
            print(f"REC -> {path}")
        else:
            writer.release(); writer = None
            print("stop")
    elif key == ord('q'):
        break

if writer is not None:
    writer.release()
cap.release()
cv2.destroyAllWindows()
print(f"fatto. {n_clip} clip in {VIDEOS}")
