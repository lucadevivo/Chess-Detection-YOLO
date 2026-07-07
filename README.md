# Chess Detection YOLO - Progetto AI Lab

Sistema di visione artificiale per il riconoscimento e la mappatura in tempo reale di una scacchiera fisica tramite YOLOv8. Il software identifica i pezzi, ne corregge la classificazione tramite logica predefinita e proietta le posizioni su un'interfaccia 2D zenitale.

## Funzionalità principali

Il sistema processa il flusso video per estrarre la posizione dei pezzi e degli angoli della scacchiera. Include un meccanismo di calibrazione manuale che permette di regolare i quattro angoli della scacchiera tramite trascinamento, garantendo una proiezione accurata (omografia) anche con diverse inclinazioni della telecamera. 

È stata implementata una logica di correzione per gestire eventuali errori del modello YOLO, come lo scambio tra Re e Regina, basandosi sulla configurazione standard del gioco.

## Struttura del repository

- `src/main.py`: Script principale che gestisce il loop video e l'interfaccia.
- `src/vision.py`: Gestione dell'inferenza del modello e correzione logica.
- `src/mapping.py`: Calcolo delle matrici di omografia per la vista 2D.
- `src/graphics.py`: Funzioni per il rendering della scacchiera virtuale.
- `scansiona_cam.py`: Utility per l'identificazione degli indici delle periferiche video.
- `best.pt`: Pesi del modello YOLOv8.

## Requisiti e Installazione

Il progetto richiede Python 3.x e le seguenti librerie:
```bash
pip install ultralytics opencv-python numpy
```

## Modalità d'uso

Per avviare l'applicazione, è consigliabile prima verificare l'indice della telecamera con lo script di scansione e poi lanciare il main:

1. `python scansiona_cam.py`
2. `python src/main.py`

Durante l'esecuzione, utilizzare il mouse per allineare i punti rossi agli angoli della scacchiera reale.

## Web app

Riconoscimento della scacchiera + valutazione stile chess.com nel browser: rileva i
pezzi via YOLOv8, costruisce la posizione (FEN) e la valuta con Stockfish (barra di
vantaggio + mossa migliore con freccia). Codice in `web/`.

### Prerequisiti
- **Docker** (unica dipendenza per l'utente finale), oppure per l'avvio manuale: Python 3.12 + Stockfish.
- Un **browser** moderno con webcam (Chrome/Edge/Firefox/Safari).

### Avvio con Docker (consigliato — Linux / macOS / Windows)
```bash
docker build -t chess-vision .
docker run --rm -p 8000:8000 chess-vision
# apri http://localhost:8000
```
La webcam viene letta dal **browser** (getUserMedia): nessun passthrough di device,
quindi funziona su qualsiasi sistema operativo con Docker Desktop/Engine. `getUserMedia`
richiede `localhost` (ok con `-p`) o HTTPS.

### Avvio senza Docker
```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install -r web/requirements.txt
# installa Stockfish: Debian/Ubuntu `apt install stockfish`, macOS `brew install stockfish`,
# Arch `pacman -S stockfish`, Windows: scarica il binario e mettilo nel PATH
uvicorn web.app:app --host 0.0.0.0 --port 8000
```

### Uso
1. **Cattura** un fotogramma della scacchiera inquadrata.
2. Trascina i **4 punti** sui marker d'angolo stampati (L / ★ / ■ / ▲); partono già
   pre-posizionati dal rilevamento.
3. Scegli **da che lato gioca il Bianco** e **di chi è il turno**.
4. **Analizza**: ottieni la scacchiera 2D, la barra di valutazione e la mossa migliore.

### Test
```bash
pip install pytest
python -m pytest tests/ -q
```

### Limiti noti
Da una singola foto (posizione senza storico) **arrocco** ed **en passant** non sono
deducibili e non sono considerati; scacco, matto e mosse legali sì (Stockfish).

---
Sviluppato da Luca De Vivo per il corso di AI Lab.
