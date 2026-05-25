# src/vision.py
from ultralytics import YOLO

def applica_euristica_re_regina(pezzi):
    """
    Corregge le allucinazioni visive di YOLO applicando le regole degli scacchi.
    """
    for colore in ['white', 'black']:
        regine = [p for p in pezzi if p['classe'] == f'{colore}-queen']
        re = [p for p in pezzi if p['classe'] == f'{colore}-king']
        
        if len(regine) > 1 and len(re) == 0:
            regine_ordinate = sorted(regine, key=lambda x: x['conf'], reverse=True)
            pezzo_da_correggere = regine_ordinate[1]
            pezzo_da_correggere['classe'] = f'{colore}-king'
            print(f"🔧 Correzione Logica: Convertita {colore}-queen in {colore}-king")
            
        elif len(re) > 1 and len(regine) == 0:
            re_ordinati = sorted(re, key=lambda x: x['conf'], reverse=True)
            pezzo_da_correggere = re_ordinati[1]
            pezzo_da_correggere['classe'] = f'{colore}-queen'
            print(f"🔧 Correzione Logica: Convertito {colore}-king in {colore}-queen")

    return pezzi


def rileva_elementi(frame, model, conf_thresh=0.40, iou_thresh=0.75):
    """
    Esegue YOLO direttamente su un frame OpenCV (numpy array) in memoria.
    Prende il modello già caricato esternamente per garantire alti FPS.
    """
    # Eseguiamo il predict direttamente sulla matrice del frame live
    # verbose=False disattiva le scritte di YOLO nel terminale per non intasarlo durante il video
    results = model.predict(source=frame, conf=conf_thresh, iou=iou_thresh, save=False, show=False, verbose=False)[0]

    angoli_temp = {}
    pezzi_rilevati = []
    class_names = results.names

    for box in results.boxes:
        xyxy = box.xyxy[0].cpu().numpy()
        cls_id = int(box.cls[0].cpu().numpy())
        class_name = class_names[cls_id]
        conf = float(box.conf[0].cpu().numpy())
        
        cx = int((xyxy[0] + xyxy[2]) / 2)
        cy = int((xyxy[1] + xyxy[3]) / 2)
        
        if "corner" in class_name:
            if class_name not in angoli_temp or conf > angoli_temp[class_name]["conf"]:
                angoli_temp[class_name] = {"punto": (cx, cy), "conf": conf}
        else:
            base_x = int((xyxy[0] + xyxy[2]) / 2)
            
            altezza_box = xyxy[3] - xyxy[1]
            # Abbassiamo la spinta al 5% per non distorcere le colonne laterali
            base_y = int(xyxy[3] - (altezza_box * 0.05))
            
            pezzi_rilevati.append({
                "classe": class_name,
                "punto_reale": (base_x, base_y),
                "conf": conf
            })

    angoli = {k: v["punto"] for k, v in angoli_temp.items()}
    pezzi_rilevati = applica_euristica_re_regina(pezzi_rilevati)
    
    return angoli, pezzi_rilevati