# src/main.py
import cv2
import collections
import numpy as np
from ultralytics import YOLO
from vision import rileva_elementi
from mapping import calcola_omografia, proietta_pezzi
from graphics import render_scacchiera

# ========================================================
# VARIABILI GLOBALI PER IL MOUSE
# ========================================================
angoli_manuali = None
punto_in_trascinamento = None
scala_x = 1.0
scala_y = 1.0
w_nuova_f = 0

def mouse_callback(event, x, y, flags, param):
    """
    Funzione catturata da OpenCV per gestire i click e i trascinamenti del mouse.
    """
    global angoli_manuali, punto_in_trascinamento, scala_x, scala_y, w_nuova_f
    
    # Se la calibrazione non è iniziata, ignora il mouse
    if angoli_manuali is None:
        return
        
    # Ignora i click sulla metà destra dello schermo (dove c'è la scacchiera 2D)
    if x > w_nuova_f:
        return

    # Convertiamo le coordinate dello schermo nella risoluzione reale della telecamera
    real_x = int(x * scala_x)
    real_y = int(y * scala_y)

    if event == cv2.EVENT_LBUTTONDOWN:
        # Quando premi il click sinistro, cerca il pallino rosso più vicino
        min_dist = float('inf')
        closest_idx = -1
        for i, pt in enumerate(angoli_manuali):
            dist = np.hypot(pt[0] - real_x, pt[1] - real_y)
            # Area di cattura bella larga (60 pixel) per afferrare il punto facilmente
            if dist < 60:  
                if dist < min_dist:
                    min_dist = dist
                    closest_idx = i
        
        if closest_idx != -1:
            punto_in_trascinamento = closest_idx

    elif event == cv2.EVENT_MOUSEMOVE:
        # Quando muovi il mouse (tenendo premuto), sposta le coordinate del punto
        if punto_in_trascinamento is not None:
            angoli_manuali[punto_in_trascinamento] = [real_x, real_y]

    elif event == cv2.EVENT_LBUTTONUP:
        # Rilasciando il click, sgancia il punto
        punto_in_trascinamento = None


def main():
    global angoli_manuali, scala_x, scala_y, w_nuova_f
    
    print("🧠 1. Caricamento del modello YOLOv8 in memoria...")
    model = YOLO('best.pt')
    
    print("📷 2. Inizializzazione della videocamera dello Smartphone...")
    URL_TELEFONO = "http://192.168.0.142:4747/video" 
    cap = cv2.VideoCapture(URL_TELEFONO)
    
    if not cap.isOpened():
        print("❌ Errore critico: Impossibile accedere alla videocamera.")
        return

    print("\n🚀 APPLICAZIONE INTERFACCIA UNICA AVVIATA!")
    print("-> FASE 1: Lascia che YOLO trovi i marker. Poi TRASCINA i punti col MOUSE per correggere al millimetro.")
    print("-> FASE 2: Premi INVIO per confermare e giocare.")
    print("-> Premi 'R' per resettare, 'Q' per uscire.\n")

    M_memoria = None
    NUM_FRAME_MEMORIA = 5
    buffer_storico = collections.deque(maxlen=NUM_FRAME_MEMORIA)
    calibrazione_completata = False
    
    ALTEZZA_APP = 600

    # Inizializziamo la finestra dell'applicazione e le attacchiamo il MOUSE
    cv2.namedWindow('Chess Vision App', cv2.WINDOW_AUTOSIZE)
    cv2.setMouseCallback('Chess Vision App', mouse_callback)

    while True:
        ret, frame = cap.read()
        if not ret:
            print("❌ Errore: Frame non ricevuto.")
            break

        # Calcoliamo le proporzioni per il ridimensionamento della dashboard
        h_f, w_f = frame.shape[:2]
        w_nuova_f = int(w_f * (ALTEZZA_APP / h_f))
        
        # Aggiorniamo le scale globali usate dal mouse
        scala_x = w_f / w_nuova_f
        scala_y = h_f / ALTEZZA_APP

        angoli, pezzi = rileva_elementi(frame, model)
        griglia_pezzi = [[" . " for _ in range(8)] for _ in range(8)]

        # ========================================================
        # FASE 1: CALIBRAZIONE MANUALE
        # ========================================================
        if not calibrazione_completata:
            
            # Se è la prima volta (angoli_manuali è vuoto), usa YOLO e mapping.py per il calcolo iniziale
            if angoli_manuali is None:
                try:
                    M_corrente = calcola_omografia(angoli)
                    M_inv = np.linalg.inv(M_corrente)
                    angoli_virtuali = np.array([[[0, 0]], [[1200, 0]], [[1200, 1200]], [[0, 1200]]], dtype=np.float32)
                    angoli_reali = cv2.perspectiveTransform(angoli_virtuali, M_inv)
                    
                    # Estraiamo i 4 vertici calcolati da YOLO e li SALVIAMO PER IL MOUSE
                    angoli_manuali = np.array([pt[0] for pt in angoli_reali], dtype=np.float32)
                except ValueError:
                    pass # Finché YOLO non vede tutti e 4 i marker, non fa niente
            
            # Se la griglia è apparsa, ignoriamo YOLO e usiamo SOLO i punti trascinabili!
            if angoli_manuali is not None:
                # Calcoliamo la matrice dell'Omografia basandoci ESATTAMENTE sui 4 pallini manuali
                pts_dst = np.array([[0, 0], [1200, 0], [1200, 1200], [0, 1200]], dtype=np.float32)
                M_memoria = cv2.getPerspectiveTransform(angoli_manuali, pts_dst)

                # Disegniamo la griglia verde e i pallini trascinabili
                cv2.polylines(frame, [np.int32(angoli_manuali)], isClosed=True, color=(0, 255, 0), thickness=3)
                for pt in angoli_manuali:
                    px, py = int(pt[0]), int(pt[1])
                    # Disegniamo un pallino rosso bello grosso e un bordino bianco per evidenziarlo
                    cv2.circle(frame, (px, py), radius=10, color=(0, 0, 255), thickness=-1)
                    cv2.circle(frame, (px, py), radius=10, color=(255, 255, 255), thickness=2)
                    
                cv2.putText(frame, "TRASCINA I PUNTINI COL MOUSE", (20, 30), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2, cv2.LINE_AA)
                cv2.putText(frame, "POI PREMI INVIO PER CONFERMARE", (20, 60), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2, cv2.LINE_AA)
            else:
                cv2.putText(frame, "INQUADRA I 4 MARKER ARANCIONI...", (20, 40), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2, cv2.LINE_AA)

            # Scacchiera Grigia
            img_scacchiera_2d = render_scacchiera(griglia_pezzi)
            img_grigia = cv2.cvtColor(img_scacchiera_2d, cv2.COLOR_BGR2GRAY)
            img_scacchiera_finale = cv2.cvtColor(img_grigia, cv2.COLOR_GRAY2BGR)

        # ========================================================
        # FASE 2: GIOCO ATTIVO (Tracciamento e Omografia Congelati)
        # ========================================================
        else:
            try:
                # Disegniamo il perimetro BLU (Fisso)
                cv2.polylines(frame, [np.int32(angoli_manuali)], isClosed=True, color=(255, 0, 0), thickness=2)
                cv2.putText(frame, "GIOCO IN CORSO (Tasto 'R' per resettare)", (20, 40), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2, cv2.LINE_AA)
            except Exception:
                pass

            # Tracciamento dei pezzi
            scacchiera_istante_corrente = proietta_pezzi(pezzi, M_memoria)
            buffer_storico.append(scacchiera_istante_corrente)
            
            if len(buffer_storico) > 0:
                for r in range(8):
                    for c in range(8):
                        voti_casella = [storico[r][c] for storico in buffer_storico]
                        griglia_pezzi[r][c] = max(set(voti_casella), key=voti_casella.count)
            
            img_scacchiera_finale = render_scacchiera(griglia_pezzi)

        # ========================================================
        # COSTRUZIONE DELLA DASHBOARD
        # ========================================================
        frame_resized = cv2.resize(frame, (w_nuova_f, ALTEZZA_APP))
        board_resized = cv2.resize(img_scacchiera_finale, (ALTEZZA_APP, ALTEZZA_APP))
        
        dashboard_unica = np.hstack((frame_resized, board_resized))
        cv2.imshow('Chess Vision App', dashboard_unica)

        # ========================================================
        # TASTIERA
        # ========================================================
        key = cv2.waitKey(1) & 0xFF
        
        if key == 13 and M_memoria is not None and not calibrazione_completata: # INVIO
            calibrazione_completata = True
            print("✅ Calibrazione Manuale confermata! Scacchiera bloccata e attiva.")
            
        elif key == ord('r'): # RESET
            calibrazione_completata = False
            angoli_manuali = None # Cancella la calibrazione e fa ricominciare da YOLO
            buffer_storico.clear()
            print("🔄 Reset. Lascia inquadrare a YOLO la prima stima...")
            
        elif key == ord('q'): # ESCI
            break

    cap.release()
    cv2.destroyAllWindows()
    print("👋 Applicazione chiusa correttamente.")

if __name__ == "__main__":
    main()