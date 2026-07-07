"""Wrapper del rilevamento YOLO esistente (src/vision.py)."""
import os
import sys

_SRC = os.path.join(os.path.dirname(__file__), "..", "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from ultralytics import YOLO  # noqa: E402
import vision                 # noqa: E402  (modulo esistente in src/)

_model = None


def load_model(path):
    """Carica il modello YOLO una volta e lo memorizza."""
    global _model
    _model = YOLO(path)
    return _model


def detect(frame_bgr, model=None):
    """frame BGR -> {pieces, corners} usando la logica esistente."""
    m = model or _model
    if m is None:
        raise RuntimeError("modello non caricato: chiama load_model() prima")
    angoli, pezzi = vision.rileva_elementi(frame_bgr, m)
    return {"pieces": pezzi, "corners": angoli}
