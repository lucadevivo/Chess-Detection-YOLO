#!/usr/bin/env python
"""
Stage 3: carica frame + label YOLO corrette su Roboflow, in un batch dedicato.

Serve la API key in env:  export ROBOFLOW_API_KEY=xxxx
Uso:
    python dataset_pipeline/upload.py --workspace <ws> --project <proj> \
        [--batch auto_lifecam_2026-07-07] [--tag auto_lifecam] [--split train] [--dry-run]

Legge dataset_pipeline/out/{frames,labels,labelmap.json}.
Le immagini finiscono tutte nel batch/tag indicato -> le ritrovi filtrando in UI
e controlli SOLO quelle. Ogni frame senza .txt (o .txt vuoto) viene saltato.
"""
import argparse, os, sys, json, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "out"


def main():
    today = datetime.date.today().isoformat()
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", required=True)
    ap.add_argument("--project", required=True)
    ap.add_argument("--batch", default=f"auto_lifecam_{today}")
    ap.add_argument("--tag", default="auto_lifecam")
    ap.add_argument("--split", default="train", choices=["train", "valid", "test"])
    ap.add_argument("--is-prediction", action="store_true",
                    help="carica come predizioni da approvare invece che annotazioni")
    ap.add_argument("--dry-run", action="store_true", help="elenca cosa caricherebbe, non carica")
    args = ap.parse_args()

    key = os.environ.get("ROBOFLOW_API_KEY")
    if not key and not args.dry_run:
        print("manca ROBOFLOW_API_KEY in env"); sys.exit(1)

    frames_dir = OUT / "frames"
    labels_dir = OUT / "labels"
    labelmap = OUT / "labelmap.names"
    if not frames_dir.exists():
        print(f"manca {frames_dir}: lancia prima prelabel.py"); sys.exit(1)

    frames = sorted(frames_dir.glob("*.jpg"))
    jobs = []
    for img in frames:
        txt = labels_dir / f"{img.stem}.txt"
        if not txt.exists() or not txt.read_text().strip():
            print(f"skip (nessun label): {img.name}")
            continue
        jobs.append((img, txt))

    print(f"{len(jobs)}/{len(frames)} frame con label -> batch '{args.batch}', tag '{args.tag}', split '{args.split}'")
    if args.dry_run:
        for img, txt in jobs:
            n = len([l for l in txt.read_text().splitlines() if l.strip()])
            print(f"  {img.name}  ({n} box)")
        return

    from roboflow import Roboflow
    rf = Roboflow(api_key=key)
    project = rf.workspace(args.workspace).project(args.project)

    ok = 0
    for img, txt in jobs:
        try:
            res = project.single_upload(
                image_path=str(img),
                annotation_path=str(txt),
                annotation_labelmap=str(labelmap),
                split=args.split,
                batch_name=args.batch,
                tag_names=[args.tag],
                is_prediction=args.is_prediction,
                num_retry_uploads=2,
            )
            ok += 1
            print(f"OK {img.name}: {res}")
        except Exception as e:
            print(f"FAIL {img.name}: {e}")

    print(f"\ncaricati {ok}/{len(jobs)}. In Roboflow filtra per batch '{args.batch}' e rivedi solo quelli.")


if __name__ == "__main__":
    main()
