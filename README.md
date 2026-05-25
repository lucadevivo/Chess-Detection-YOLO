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

---
Sviluppato da Luca De Vivo per il corso di AI Lab.
