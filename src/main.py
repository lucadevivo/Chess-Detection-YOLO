# main.py
import cv2
from vision import rileva_elementi
from mapping import calcola_omografia, proietta_pezzi
from graphics import render_scacchiera

def main():
    NOME_FOTO = 'foto_test.jpg'
    
    print("1. Avvio inferenza YOLO...")
    angoli, pezzi = rileva_elementi(NOME_FOTO)
    
    print("2. Calcolo geometria e omografia...")
    try:
        M = calcola_omografia(angoli)
    except ValueError as e:
        print(f"ERRORE: {e}")
        return
        
    print("3. Generazione matrice virtuale...")
    scacchiera_virtuale = proietta_pezzi(pezzi, M)
    
    print("4. Rendering dell'immagine finale...")
    img_finale = render_scacchiera(scacchiera_virtuale)
    
    cv2.imwrite('scacchiera_2D_output.png', img_finale)
    print("🎯 Operazione completata! Risultato salvato in 'scacchiera_2D_output.png'")
    
    # Mostra a schermo ridimensionato
    altezza_schermo = 800
    fattore = altezza_schermo / img_finale.shape[0]
    img_ridimensionata = cv2.resize(img_finale, (int(img_finale.shape[1] * fattore), altezza_schermo))
    
    cv2.imshow('Chess.com Replica', img_ridimensionata)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()