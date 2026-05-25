# scansiona_cam.py
import cv2

print("🔍 Scansione degli indici video disponibili nel sistema...")
dispositivi_trovati = False

for i in range(10):
    # Proviamo ad aprire l'indice con il backend nativo Linux
    cap = cv2.VideoCapture(i, cv2.CAP_V4L2)
    if cap.isOpened():
        ret, frame = cap.read()
        if ret:
            print(f"✅ INDICE [{i}]: FUNZIONA! Cattura video attiva. (Risoluzione: {frame.shape[1]}x{frame.shape[0]})")
            dispositivi_trovati = True
        else:
            print(f"⚠️ INDICE [{i}]: Rilevato, ma NON invia immagini (Canale metadati/UVC).")
        cap.release()

if not dispositivi_trovati:
    print("\n❌ Nessun indice ha restituito un flusso video valido.")
    print("Consiglio: Controlla i permessi o digita nel terminale di sistema: v4l2-ctl --list-devices")