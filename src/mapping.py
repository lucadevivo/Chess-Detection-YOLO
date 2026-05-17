# mapping.py
import cv2
import numpy as np

def calcola_omografia(angoli, dim_scacchiera=1200):
    """
    Calcola la matrice di trasformazione prospettica M basata sui 4 angoli.
    Include un offset per ignorare il bordo bianco fisico della scacchiera.
    """
    classi_richieste = ['L-corner', 'star-corner', 'square-corner', 'triangle-corner']
    if len(angoli) < 4:
        raise ValueError("Mancano marker d'angolo. Impossibile raddrizzare.")

    pts_src = np.array([
        angoli['L-corner'], angoli['star-corner'],
        angoli['square-corner'], angoli['triangle-corner']
    ], dtype=np.float32)

    # Calcoliamo la dimensione di una singola casella
    dim_casella = dim_scacchiera // 8
    
    # Impostiamo l'offset stimato per il bordo bianco (circa il 40% di una casella)
    # NOTA: Se i pezzi risultano ancora un po' spostati, puoi variare questo 0.40 (es. 0.30 o 0.50)
    OFFSET = int(dim_casella * 0.40)

    # Mappiamo i marker OLTRE i confini della griglia giocabile (0-1200)
    pts_dst = np.array([
        [dim_scacchiera + OFFSET, -OFFSET],                 # L-corner -> Fuori in alto a destra
        [dim_scacchiera + OFFSET, dim_scacchiera + OFFSET], # star-corner -> Fuori in basso a destra
        [-OFFSET, dim_scacchiera + OFFSET],                 # square-corner -> Fuori in basso a sinistra
        [-OFFSET, -OFFSET]                                  # triangle-corner -> Fuori in alto a sinistra
    ], dtype=np.float32)

    return cv2.getPerspectiveTransform(pts_src, pts_dst)


def proietta_pezzi(pezzi_rilevati, M, dim_scacchiera=1200):
    """
    Applica l'omografia ai pezzi e li posiziona in una matrice 8x8.
    """
    dim_casella = dim_scacchiera // 8
    scacchiera_virtuale = [[" . " for _ in range(8)] for _ in range(8)]

    for pezzo in pezzi_rilevati:
        px, py = pezzo["punto_reale"]
        punto_3d = np.array([[[px, py]]], dtype=np.float32)
        
        # Applichiamo la trasformazione
        punto_2d = cv2.perspectiveTransform(punto_3d, M)
        
        # Estraiamo le coordinate proiettate
        x_proiettato = punto_2d[0][0][0]
        y_proiettato = punto_2d[0][0][1]
        
        colonna = int(x_proiettato // dim_casella)
        riga = int(y_proiettato // dim_casella)
        
        # Inseriamo il pezzo solo se cade fisicamente dentro la griglia 8x8
        if 0 <= colonna < 8 and 0 <= riga < 8:
            colore = 'w' if 'white' in pezzo["classe"] else 'b'
            tipo = ''
            if 'pawn' in pezzo["classe"]: tipo = 'p'
            elif 'rook' in pezzo["classe"]: tipo = 'r'
            elif 'knight' in pezzo["classe"]: tipo = 'n'
            elif 'bishop' in pezzo["classe"]: tipo = 'b'
            elif 'queen' in pezzo["classe"]: tipo = 'q'
            elif 'king' in pezzo["classe"]: tipo = 'k'
            
            scacchiera_virtuale[riga][colonna] = f"{colore}{tipo}"
            
    return scacchiera_virtuale