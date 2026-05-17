# vision.py
from ultralytics import YOLO

def applica_euristica_re_regina(pezzi):
    """
    Corregge le allucinazioni visive di YOLO applicando le regole degli scacchi.
    Se trova 2 Regine e 0 Re (o viceversa), corregge il pezzo con la confidenza minore.
    """
    for colore in ['white', 'black']:
        # Filtriamo i pezzi per trovare re e regine del colore corrente
        regine = [p for p in pezzi if p['classe'] == f'{colore}-queen']
        re = [p for p in pezzi if p['classe'] == f'{colore}-king']
        
        # CASO 1: Troppe Regine, manca il Re
        if len(regine) > 1 and len(re) == 0:
            # Ordina le regine dalla più sicura alla meno sicura
            regine_ordinate = sorted(regine, key=lambda x: x['conf'], reverse=True)
            # Prende la seconda regina (quella con confidenza minore) e la fa diventare Re
            pezzo_da_correggere = regine_ordinate[1]
            pezzo_da_correggere['classe'] = f'{colore}-king'
            print(f"🔧 Correzione Logica: Convertita {colore}-queen ({pezzo_da_correggere['conf']:.2f}) in {colore}-king")
            
        # CASO 2: Troppi Re, manca la Regina
        elif len(re) > 1 and len(regine) == 0:
            # Ordina i re dal più sicuro al meno sicuro
            re_ordinati = sorted(re, key=lambda x: x['conf'], reverse=True)
            # Prende il secondo re (quello con confidenza minore) e lo fa diventare Regina
            pezzo_da_correggere = re_ordinati[1]
            pezzo_da_correggere['classe'] = f'{colore}-queen'
            print(f"🔧 Correzione Logica: Convertito {colore}-king ({pezzo_da_correggere['conf']:.2f}) in {colore}-queen")

    return pezzi


def rileva_elementi(percorso_foto, percorso_modello='best.pt', conf_thresh=0.40, iou_thresh=0.75):
    """
    Esegue YOLO sull'immagine e restituisce i marker d'angolo e i pezzi rilevati.
    """
    model = YOLO(percorso_modello)
    results = model.predict(source=percorso_foto, conf=conf_thresh, iou=iou_thresh, save=False, show=False)[0]

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
            # Filtro per tenere solo l'angolo con la confidenza più alta
            if class_name not in angoli_temp or conf > angoli_temp[class_name]["conf"]:
                angoli_temp[class_name] = {"punto": (cx, cy), "conf": conf}
        else:
            base_x = int((xyxy[0] + xyxy[2]) / 2)
            base_y = int(xyxy[3])
            pezzi_rilevati.append({
                "classe": class_name,
                "punto_reale": (base_x, base_y),
                "conf": conf
            })

    # Puliamo il dizionario degli angoli per passarlo alla geometria
    angoli = {k: v["punto"] for k, v in angoli_temp.items()}
    
    # ---------------------------------------------------------
    # APPLICHIAMO LA CORREZIONE SUI PEZZI PRIMA DI RESTITUIRLI!
    # ---------------------------------------------------------
    pezzi_rilevati = applica_euristica_re_regina(pezzi_rilevati)
    
    return angoli, pezzi_rilevati