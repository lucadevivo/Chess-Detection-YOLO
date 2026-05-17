# graphics.py
import cv2
import numpy as np

def overlay_transparent(background, overlay, x, y):
    background_width, background_height = background.shape[1], background.shape[0]

    if x >= background_width or y >= background_height:
        return background

    h, w = overlay.shape[0], overlay.shape[1]

    if x + w > background_width:
        w = background_width - x
        overlay = overlay[:, :w]
    if y + h > background_height:
        h = background_height - y
        overlay = overlay[:h, :]

    if overlay.shape[2] < 4:
        background[y:y+h, x:x+w] = overlay[:, :, :3]
        return background

    overlay_image = overlay[..., :3]
    mask = overlay[..., 3:] / 255.0

    background[y:y+h, x:x+w] = (1.0 - mask) * background[y:y+h, x:x+w] + mask * overlay_image
    return background

def render_scacchiera(scacchiera_virtuale, percorso_sfondo='pezzi/150.png', dim_scacchiera=1200):
    """
    Genera l'immagine finale della scacchiera con pezzi e coordinate.
    """
    img_output = cv2.imread(percorso_sfondo)
    if img_output is None:
        raise FileNotFoundError(f"Impossibile trovare {percorso_sfondo}")

    img_output = cv2.resize(img_output, (dim_scacchiera, dim_scacchiera))
    if img_output.shape[2] == 4:
        img_output = img_output[:, :, :3]

    dim_casella = dim_scacchiera // 8
    lettere_colonne = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
    
    BROWN_CHESS = (90, 140, 120)
    CREAM_CHESS = (215, 235, 235)
    FONT_SCACCHI = cv2.FONT_HERSHEY_DUPLEX

    for riga in range(8):
        for colonna in range(8):
            x1 = colonna * dim_casella
            y1 = riga * dim_casella
            
            is_casella_chiara = ((riga + colonna) % 2 == 0)
            colore_testo = BROWN_CHESS if is_casella_chiara else CREAM_CHESS
            
            if colonna == 0:
                cv2.putText(img_output, str(8 - riga), (x1 + 10, y1 + 32), FONT_SCACCHI, 0.7, colore_testo, 2, cv2.LINE_AA)
                
            if riga == 7:
                cv2.putText(img_output, lettere_colonne[colonna], (x1 + dim_casella - 28, y1 + dim_casella - 10), FONT_SCACCHI, 0.7, colore_testo, 2, cv2.LINE_AA)

            contenuto = scacchiera_virtuale[riga][colonna].strip()
            if contenuto != ".":
                try:
                    img_pezzo = cv2.imread(f"pezzi/{contenuto}.png", cv2.IMREAD_UNCHANGED)
                    if img_pezzo is not None:
                        if img_pezzo.shape[0] != dim_casella or img_pezzo.shape[1] != dim_casella:
                            img_pezzo = cv2.resize(img_pezzo, (dim_casella, dim_casella))
                        img_output = overlay_transparent(img_output, img_pezzo, x1, y1)
                except Exception:
                    pass

    return img_output