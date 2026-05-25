# Chess Detection YOLO - AILab Project

Questo progetto implementa un sistema di visione artificiale per il rilevamento e la mappatura in tempo reale di una scacchiera fisica utilizzando **YOLOv8**. Il sistema identifica i pezzi sulla scacchiera, corregge eventuali errori di classificazione tramite euristiche logiche e proietta la posizione dei pezzi su una scacchiera 2D virtuale.

## 🚀 Caratteristiche principali

- **Rilevamento in Tempo Reale**: Utilizza un modello YOLOv8 (`best.pt`) addestrato per riconoscere pezzi e angoli della scacchiera.
- **Calibrazione Dinamica**: Gestione degli angoli della scacchiera con possibilità di trascinamento manuale dei punti per una proiezione perfetta.
- **Mappatura 2D (Omografia)**: Trasformazione della prospettiva dalla telecamera a una vista zenitale 2D.
- **Euristiche Anti-Allucinazione**: Correzione automatica della confusione tra Re e Regina basata sulle regole degli scacchi.
- **Scansione Dispositivi**: Script incluso per identificare correttamente gli indici delle telecamere collegate.

## 📂 Struttura del Progetto

- `src/main.py`: Punto di ingresso principale dell'applicazione.
- `src/vision.py`: Gestione dell'inferenza YOLO e logica di correzione dei pezzi.
- `src/mapping.py`: Calcolo della matrice di omografia e proiezione delle coordinate.
- `src/graphics.py`: Rendering della scacchiera 2D e sovrapposizione grafica.
- `scansiona_cam.py`: Utility per trovare l'ID corretto della fotocamera.
- `best.pt`: Pesi del modello YOLOv8 addestrato.
- `pezzi/`: Asset grafici dei pezzi per la visualizzazione 2D.

## 🛠️ Installazione

1. Clona il repository:
   ```bash
   git clone git@github.com:lucadevivo/Chess-Detection-YOLO.git
   cd Chess-Detection-YOLO
   ```

2. Installa le dipendenze:
   ```bash
   pip install ultralytics opencv-python numpy
   ```

## 💻 Utilizzo

1. **Trova la tua camera**:
   ```bash
   python scansiona_cam.py
   ```

2. **Avvia il sistema**:
   ```bash
   python src/main.py
   ```

3. **Interazione**:
   - Una volta avviato, clicca e trascina i punti rossi per allinearli ai quattro angoli della tua scacchiera fisica.
   - Il sistema inizierà a mappare i pezzi rilevati sulla finestra della scacchiera 2D.

---
Sviluppato per il corso di AI Lab da **Luca De Vivo**.
