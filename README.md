# Chess Vision

Riconosce una scacchiera fisica dalla webcam e analizza la posizione. I pezzi vengono
individuati con un modello YOLOv8, la posizione viene ricostruita come FEN e valutata con
Stockfish: l'app mostra chi è in vantaggio e qual è la mossa migliore.

Il progetto nasce per il corso di AI Lab. Ci sono due modalità: l'app desktop originale
(finestra OpenCV) e una web app in Docker.

## Come funziona

La webcam inquadra la scacchiera. Il modello rileva i pezzi e i quattro marker agli angoli
del foglio; da questi si ricava l'omografia che raddrizza la vista e assegna ogni pezzo alla
sua casella. La griglia 8×8 così ottenuta viene tradotta in una FEN, usando il lato del
Bianco e il turno indicati dall'utente, e passata a Stockfish per valutazione e mossa
migliore.

## Requisiti

- Docker, oppure Python 3.12 e Stockfish per l'avvio manuale.
- Un browser con accesso alla webcam.

## Avvio con Docker

```
docker build -t chess-vision .
docker run --rm -p 8000:8000 chess-vision
```

Apri http://localhost:8000. La webcam viene letta dal browser, quindi non serve collegare
periferiche al container e l'app si comporta allo stesso modo su Linux, macOS e Windows.

## Avvio senza Docker

```
python -m venv .venv && source .venv/bin/activate
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install -r web/requirements.txt
uvicorn web.app:app --port 8000
```

Serve anche il binario di Stockfish nel PATH: `apt install stockfish` su Debian/Ubuntu,
`brew install stockfish` su macOS, `pacman -S stockfish` su Arch, oppure il binario da
stockfishchess.org su Windows.

## Uso

1. Inquadra la scacchiera e premi Cattura.
2. Trascina i quattro punti sui marker agli angoli (L, stella, quadrato, triangolo): partono
   già vicino, li sistemi per precisione.
3. Indica da che lato gioca il Bianco e di chi è il turno.
4. Premi Analizza.

## Struttura

- `web/` — la web app: FastAPI (`app.py`), rilevamento (`detect.py`), costruzione della FEN
  (`board.py`), motore Stockfish (`engine.py`), frontend in `web/static/`.
- `src/` — l'app desktop originale e la logica condivisa di visione e omografia.
- `dataset_pipeline/` — script per registrare video, estrarne i frame, pre-etichettarli col
  modello e caricarli su Roboflow per ampliare il dataset.
- `best.pt` — pesi del modello YOLOv8.
- `tests/` — test di `board`, `engine` e API.

## Test

```
pip install pytest
python -m pytest tests/ -q
```

## Limiti

L'analisi parte da una singola immagine, senza la storia della partita: arrocco ed en
passant non sono deducibili e non vengono considerati. Scacco, matto e mosse legali sì. La
precisione dipende dall'inquadratura e dalla luce; per questo i quattro punti d'angolo si
possono correggere a mano prima di analizzare.

---

Progetto per il corso di AI Lab — Luca De Vivo.
