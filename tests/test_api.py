import io
import os

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

MODEL = os.path.join(os.path.dirname(__file__), "..", "best.pt")
model_missing = not os.path.exists(MODEL)


@pytest.mark.skipif(model_missing, reason="serve best.pt")
def test_analyze_no_board_returns_corner_reason():
    # Non serve stockfish: frame senza scacchiera -> reason 'corner' prima dell'engine.
    from web.app import app
    blank = np.full((480, 640, 3), 255, np.uint8)
    ok, buf = cv2.imencode(".jpg", blank)
    files = {"image": ("f.jpg", io.BytesIO(buf.tobytes()), "image/jpeg")}
    data = {"white_side": "bottom", "turn": "w"}
    with TestClient(app) as client:   # context manager -> esegue lo startup (load_model)
        r = client.post("/analyze", files=files, data=data)
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is False
    assert body["reason"] == "corner"
