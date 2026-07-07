#!/usr/bin/env python
"""
Stage 1: video -> frame 1fps -> pre-label YOLO col modello -> preview numerate.

Uso:
    python dataset_pipeline/prelabel.py <video1.mp4> [video2.mp4 ...]

Output in dataset_pipeline/out/:
    frames/<stem>_NNNN.jpg      immagine pulita (va nel dataset)
    labels/<stem>_NNNN.txt      YOLO: <cls_id> <cx> <cy> <w> <h> normalizzati
    preview/<stem>_NNNN.jpg     stessa img con box+indice+classe disegnati (per review)
    detections.json             mappa frame -> [{idx, classe, conf}] per la review
    labelmap.json               id -> nome classe (per upload Roboflow)

Nota: i .txt sono la verita' modificabile. La preview e detections.json servono
solo a farmi (Claude) vedere cosa correggere; poi si editano i .txt.
"""
import sys, os, json, subprocess, shutil, tempfile
from pathlib import Path
import cv2
from ultralytics import YOLO

FPS = 1
CONF = 0.40
IOU = 0.75
ROOT = Path(__file__).resolve().parent
OUT = ROOT / "out"
MODEL_PATH = ROOT.parent / "best.pt"


def extract_frames(video: Path, dst: Path, stem: str) -> list[Path]:
    dst.mkdir(parents=True, exist_ok=True)
    pattern = str(dst / f"{stem}_%04d.jpg")
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error",
         "-i", str(video), "-vf", f"fps={FPS}", "-q:v", "2", pattern],
        check=True,
    )
    return sorted(dst.glob(f"{stem}_*.jpg"))


def main():
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    videos = [Path(v) for v in sys.argv[1:]]
    for v in videos:
        if not v.exists():
            print(f"manca: {v}"); sys.exit(1)

    if OUT.exists():
        shutil.rmtree(OUT)
    frames_dir = OUT / "frames"
    labels_dir = OUT / "labels"
    preview_dir = OUT / "preview"
    for d in (frames_dir, labels_dir, preview_dir):
        d.mkdir(parents=True, exist_ok=True)

    print(f"carico modello {MODEL_PATH.name}...")
    model = YOLO(str(MODEL_PATH))
    (OUT / "labelmap.json").write_text(json.dumps(model.names, indent=2))
    # .names (un nome per riga in ordine id) = formato che il SDK Roboflow parsa
    _names = [model.names[i] for i in range(len(model.names))]
    (OUT / "labelmap.names").write_text("\n".join(_names) + "\n")

    detections = {}
    total = 0
    with tempfile.TemporaryDirectory() as tmp:
        for v in videos:
            stem = v.stem.replace(" ", "_")
            print(f"\n{v.name}: estraggo frame a {FPS}fps...")
            frames = extract_frames(v, Path(tmp), stem)
            print(f"  {len(frames)} frame")
            for f in frames:
                img = cv2.imread(str(f))
                r = model.predict(source=img, conf=CONF, iou=IOU, verbose=False)[0]
                h, w = img.shape[:2]
                lines, dets = [], []
                # ordina per confidenza decrescente cosi' l'indice e' stabile
                boxes = sorted(r.boxes, key=lambda b: -float(b.conf[0]))
                for idx, b in enumerate(boxes):
                    cid = int(b.cls[0])
                    name = r.names[cid]
                    conf = float(b.conf[0])
                    cx, cy, bw, bh = b.xywhn[0].tolist()
                    lines.append(f"{cid} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}")
                    dets.append({"idx": idx, "classe": name, "conf": round(conf, 2)})
                    # disegna box + indice + classe sulla preview
                    x1, y1, x2, y2 = b.xyxy[0].tolist()
                    p1, p2 = (int(x1), int(y1)), (int(x2), int(y2))
                    cv2.rectangle(img, p1, p2, (0, 255, 0), 2)
                    cv2.putText(img, f"#{idx} {name}", (p1[0], max(0, p1[1] - 6)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2, cv2.LINE_AA)

                name_stem = f.stem
                (labels_dir / f"{name_stem}.txt").write_text("\n".join(lines))
                shutil.copy(f, frames_dir / f.name)
                cv2.imwrite(str(preview_dir / f.name), img)
                detections[name_stem] = dets
                total += 1

    (OUT / "detections.json").write_text(json.dumps(detections, indent=2, ensure_ascii=False))
    print(f"\nfatto: {total} frame in {OUT}")
    print("prossimo: Claude guarda preview/ e corregge labels/, poi upload.")


if __name__ == "__main__":
    main()
