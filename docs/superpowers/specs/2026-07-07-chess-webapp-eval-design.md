# Chess Vision Web App — Design

Data: 2026-07-07
Progetto: AILabProject (riconoscimento scacchiera YOLOv8 + OpenCV)

## Obiettivo

Trasformare l'app desktop OpenCV (`src/main.py`) in una **web app dockerizzata**
utilizzabile da chiunque, che:

1. Fa scegliere quale fotocamera usare quando ce n'è più di una.
2. Rileva la posizione dei pezzi dalla webcam e la valuta con un motore scacchistico:
   barra di valutazione stile chess.com (chi sta vincendo) + mossa migliore.
3. Fa specificare all'utente di chi è il turno e da che lato gioca il Bianco.
4. È dockerizzata così da girare su qualsiasi sistema (Linux/Mac/Windows).

Non-obiettivi (YAGNI per v1): login/multiutente, salvataggio partite, drag manuale
dei corner, riconoscimento mosse in streaming continuo, arrocco/en-passant nella FEN.

## Architettura

Web app client-server. Il core di visione esistente (`vision.py`, `mapping.py`,
`graphics.py`) viene riusato lato backend. La webcam vive **nel browser**
(`getUserMedia`): il frontend cattura un frame e lo manda al backend, che risponde
con l'analisi. Nessun passthrough di `/dev/video` nel container → cross-platform reale.
`getUserMedia` funziona su `localhost` senza HTTPS, sufficiente per chi esegue il
container in locale.

```
Browser (frontend statico)                 Backend FastAPI (in Docker)
- preview webcam + picker camera            - GET  /            -> serve frontend
- selettore lato Bianco + turno             - POST /analyze     -> riceve 1 frame JPEG
- bottone "Analizza"          --frame-->      * YOLO: pezzi + 4 corner
- barra eval + mossa (freccia) <--JSON--      * omografia -> griglia 8x8
- board 2D renderizzata                        * FEN (orientamento + colori + turno)
                                               * sanitize FEN
                                               * Stockfish -> eval + bestmove
```

Flusso di analisi (a ogni pressione di "Analizza"):
1. Il browser cattura il frame corrente della webcam e lo invia (JPEG) a `POST /analyze`
   insieme a: lato del Bianco, turno.
2. Backend: YOLO rileva pezzi (classe = colore+tipo) e i 4 corner marker.
3. Se mancano i 4 corner → risposta `{ok: false, reason: "corner"}` ("riquadra la scacchiera").
4. Omografia dai 4 corner → proiezione dei pezzi su griglia 8×8 (riusa `mapping.py`).
5. Costruzione FEN dalla griglia usando il lato del Bianco (orientamento) e i colori rilevati.
6. Sanitize FEN; se non valida → `{ok: false, reason: "fen", detail: ...}`.
7. Stockfish valuta (side-to-move = turno scelto) → `{eval_cp|mate, bestmove}`.
8. Risposta `{ok: true, fen, eval, bestmove, board}` → il frontend aggiorna barra,
   freccia e board 2D.

## Componenti

Ogni modulo ha una responsabilità unica, interfaccia chiara, testabile in isolamento.
Nuova cartella `web/` per il codice della web app; i moduli `src/*.py` esistenti restano.

### 1. `web/detect.py` — rilevamento
- `detect(frame_bgr) -> Detection` dove `Detection = {pieces: [{classe, punto_reale, conf}], corners: {nome:(x,y)}}`.
- Wrappa il modello YOLO già caricato e la logica di `src/vision.py`
  (inclusa `applica_euristica_re_regina`). Il modello (`best.pt`) è caricato una volta all'avvio.
- Dipende da: ultralytics, `best.pt`.

### 2. `web/board.py` — griglia → FEN
- `build_fen(detection, white_side, turn) -> FenResult` con
  `FenResult = {ok, fen?, grid?, reason?, detail?}`.
- Passi: omografia (riusa `mapping.calcola_omografia` + `proietta_pezzi`) → griglia 8×8;
  mappatura griglia→a1..h8 in base a `white_side` (rotazione della griglia così che la
  traversa base del Bianco = rank 1); composizione stringa FEN (placement + turno +
  `- - 0 1` per castling/en-passant/halfmove/fullmove).
- Sanitize/validazione:
  - esattamente 1 re bianco e 1 re nero; se 0 → errore; se >1 → tiene quello a conf
    maggiore, scarta gli altri (riusa lo spirito dell'euristica esistente).
  - nessun pedone su rank 1 o 8 → scartato (rilevamento errato).
  - se dopo il sanitize la posizione non è costruibile → `ok=false, reason="fen"`.
- `white_side` ∈ {bottom, top, left, right} rispetto alla vista camera.
- Dipende da: `mapping.py`, numpy.

### 3. `web/engine.py` — motore
- `analyze(fen) -> {eval_cp?, mate?, bestmove}`.
- Usa `python-chess` con il binario **Stockfish** (`chess.engine.SimpleEngine`).
- Config: `movetime ≈ 1000 ms` (costante in cima, tunabile).
- `eval_cp` = centipawn dal punto di vista del Bianco; `mate` = numero di mosse al matto
  (segno = chi matta). `bestmove` in UCI (es. `e2e4`).
- Self-check: FEN nota → `bestmove` atteso (assert in `__main__`).
- Dipende da: python-chess, binario stockfish nel PATH.

### 4. `web/app.py` — API + serving
- FastAPI. `GET /` serve `web/static/index.html`; static mount per JS/CSS.
- `POST /analyze` (multipart: image + form fields `white_side`, `turn`) →
  `detect` → `board.build_fen` → `engine.analyze`; assembla JSON come sopra.
- Carica il modello YOLO all'avvio (startup event), non per richiesta.
- Errori → JSON `{ok:false, reason, detail}`, mai 500 grezzo verso il client.

### 5. `web/static/` — frontend (HTML + CSS + JS vanilla, no framework)
- **Camera picker**: `navigator.mediaDevices.enumerateDevices()` → `<select>` dei device
  video; se >1 mostra il selettore, altrimenti usa l'unica. `getUserMedia({deviceId})`
  in un `<video>` di preview.
- **Controlli**: selettore lato Bianco (bottom/top/left/right), selettore turno (Bianco/Nero),
  bottone **Analizza**.
- **Cattura frame**: disegna il `<video>` su un `<canvas>` → `toBlob('image/jpeg')` → POST.
- **Barra eval**: barra verticale CSS bianco/nero, altezza proporzionale al vantaggio
  (cp normalizzati con clamp, es. ±10 → estremi; matto = piena). Etichetta con il valore.
- **Board 2D**: render della posizione rilevata (immagine restituita dal backend, generata
  con `graphics.render_scacchiera`, oppure ridisegnata client-side dalla `grid`).
- **Mossa migliore**: freccia dal quadrato di partenza a quello d'arrivo disegnata sulla
  board 2D (le coord algebriche non servono su una scacchiera di carta senza etichette);
  mostrata anche in testo UCI come riferimento.
- **Stati d'errore**: messaggi leggibili per `reason` = "corner" / "fen".

### 6. Docker
- `web/Dockerfile`: `FROM python:3.12-slim`; `apt-get install -y stockfish`;
  `pip install` (fastapi, uvicorn, python-multipart, ultralytics, opencv-python-headless,
  python-chess, numpy, torch CPU); copia `src/`, `web/`, `best.pt`; `CMD uvicorn web.app:app --host 0.0.0.0 --port 8000`.
- Nel container si usa `opencv-python-headless` (nessuna GUI lato server: giusto).
- `docker build -t chess-vision .` e `docker run -p 8000:8000 chess-vision`, poi
  `http://localhost:8000`.
- `requirements.txt` dedicato per la web app.

## Interfacce dati

```
Detection = { pieces: [ {classe:str, punto_reale:(int,int), conf:float} ],
              corners: { "L-corner":(x,y), "star-corner":(x,y),
                         "square-corner":(x,y), "triangle-corner":(x,y) } }

/analyze request  = multipart: image=<jpeg>, white_side="bottom|top|left|right", turn="w|b"
/analyze response = { ok:true, fen:str,
                      eval:{cp:int|null, mate:int|null},
                      bestmove:{uci:str, from:[r,c], to:[r,c]},
                      board:{ grid: [[str]] , png_b64: str } }
                  | { ok:false, reason:"corner|fen", detail:str }
```

## Gestione errori
- Corner mancanti / omografia fallita → messaggio "riquadra la scacchiera", nessun crash.
- FEN non valida (re mancante, ecc.) → messaggio esplicito, nessuna chiamata all'engine.
- Engine non disponibile → errore chiaro all'avvio (fail fast se il binario manca).
- Il client non riceve mai stacktrace: sempre JSON `{ok:false,...}`.

## Testing
- `web/board.py`: unit test griglia→FEN — posizione nota (piazzamento manuale della griglia)
  → FEN attesa; posizione impossibile (0 re / 2 re / pedone su rank 8) → `ok=false` o repair
  atteso; le 4 opzioni `white_side` producono l'orientamento giusto.
- `web/engine.py`: FEN nota (es. matto in 1) → `bestmove` atteso; self-check in `__main__`.
- Smoke test API: `POST /analyze` con un frame JPEG salvato del setup reale → risposta
  `ok:true` con FEN plausibile (il frame di test è uno dei frame LifeCam già raccolti).
- Test manuale end-to-end: `docker run`, apri browser, scegli camera/lato/turno, Analizza.

## Rischi / note
- Precisione corner automatica: se i marker sono rilevati imprecisi, i pezzi ai bordi
  possono cadere nella casella sbagliata → FEN errata. Mitigazione v1: usare il corner a
  conf massima per marker (già fatto in `vision.py`) e l'`OFFSET` di `mapping.py`.
  Drag manuale dei corner = eventuale v2.
- Il modello può ancora sbagliare qualche classe; l'eval riflette ciò che vede. Accettabile
  per un progetto dimostrativo; l'utente può ri-Analizzare.
- `getUserMedia`: richiede `localhost` o HTTPS. In locale (grader) è ok; se servito da IP
  remoto servirebbe HTTPS (fuori scope v1).
