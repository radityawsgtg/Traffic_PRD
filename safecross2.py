import cv2
import time
import winsound

print("Loading SafeCross...")
from ultralytics import YOLO
model = YOLO('yolov8s.pt') 

cap = cv2.VideoCapture(0) 

detik_minimal_menunggu = 5

total_mobil = 0
total_motor = 0
total_penyeberang = 0

id_mobil_terhitung = set()
id_motor_terhitung = set()
id_penyeberang_terhitung = set()

waktu_mulai_menunggu = {} 
status_sistem = "STANDBY"
waktu_aktif_hijau = 0 

mode_thermal = False

cv2.namedWindow("SafeCross Prototype", cv2.WND_PROP_FULLSCREEN)
cv2.setWindowProperty("SafeCross Prototype", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

while True:
    berhasil, frame = cap.read()
    if not berhasil:
            print("Failed to read video")
            break
    if mode_thermal:
        gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
        gambar_final = cv2.applyColorMap(gray, cv2.COLORMAP_JET)
    else:
        gambar_final = frame.copy()
        
    h, w, _ = frame.shape
    
    #boxes and lines
    zona_menunggu = [
        [int(w * 0), int(h * 0.35), int(w * 0.1), int(h * 0.55)],
        [int(w * 0.85), int(h * 0.35), int(w * 0.95), int(h * 0.55)]
    ]
    
    x_garis1, y_garis1 = int(w * 0), int(h * 0.5)  
    x_garis2, y_garis2 = int(w * 1), int(h * 0.5)  
    
    m = (y_garis2 - y_garis1) / (x_garis2 - x_garis1) if (x_garis2 - x_garis1) != 0 else 0
    c = y_garis1 - (m * x_garis1)

    #draw zones and lines
    for (zx1, zy1, zx2, zy2) in zona_menunggu:
        cv2.rectangle(gambar_final, (zx1, zy1), (zx2, zy2), (255, 0, 0), 2) 
        cv2.putText(gambar_final, "ZONA", (zx1, zy1-5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 0), 1)
    
    cv2.line(gambar_final, (x_garis1, y_garis1), (x_garis2, y_garis2), (0, 165, 255), 2)
    cv2.putText(gambar_final, "GARIS KENDARAAN", (x_garis2 - 50, y_garis2 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 165, 255), 1)

    hasil_deteksi = model.track(frame, persist=True, classes=[0, 2, 3, 5, 7], conf=0.15, iou=0.4, verbose=False)
    
    ada_yang_menunggu_lama = False
    track_ids_frame_ini_orang = []

    if hasil_deteksi[0].boxes.id is not None:
        boxes = hasil_deteksi[0].boxes.xyxy.cpu().numpy() 
        track_ids = hasil_deteksi[0].boxes.id.cpu().numpy()
        classes = hasil_deteksi[0].boxes.cls.cpu().numpy() 

        for box, track_id, cls in zip(boxes, track_ids, classes):
            px1, py1, px2, py2 = box
            cx = int((px1 + px2) / 2)
            cy = int((py1 + py2) / 2) 

            #pedestrians
            if int(cls) == 0:
                di_dalam_zona = False
                for (zx1, zy1, zx2, zy2) in zona_menunggu:
                    if (zx1 < cx < zx2) and (zy1 < cy < zy2):
                        di_dalam_zona = True
                        break
                
                warna_titik = (0, 0, 255)
                if di_dalam_zona:
                    warna_titik = (0, 255, 0) 
                    track_ids_frame_ini_orang.append(track_id)

                    if track_id not in id_penyeberang_terhitung:
                        total_penyeberang += 1
                        id_penyeberang_terhitung.add(track_id)

                    if track_id not in waktu_mulai_menunggu:
                        waktu_mulai_menunggu[track_id] = time.time()
                    
                    durasi_menunggu = time.time() - waktu_mulai_menunggu[track_id]
                    cv2.putText(gambar_final, f"{durasi_menunggu:.1f}s", (int(px1), int(py1)-10), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)

                    if durasi_menunggu >= detik_minimal_menunggu:
                        ada_yang_menunggu_lama = True

                cv2.circle(gambar_final, (cx, cy), 3, warna_titik, -1)
            
            #vehicles
            elif int(cls) in [2, 3, 5, 7]:
                y_harapan_garis = int((m * cx) + c)
                
                if abs(cy - y_harapan_garis) < 30:
                    if int(cls) == 3: 
                        if track_id not in id_motor_terhitung:
                            total_motor += 1
                            id_motor_terhitung.add(track_id)
                    else: 
                        if track_id not in id_mobil_terhitung:
                            total_mobil += 1
                            id_mobil_terhitung.add(track_id)
                            
                warna_kendaraan = (0, 165, 255) if int(cls) == 3 else (255, 255, 0)
                cv2.circle(gambar_final, (cx, cy), 3, warna_kendaraan, -1) 

    for id_tercatat in list(waktu_mulai_menunggu.keys()):
        if id_tercatat not in track_ids_frame_ini_orang:
            del waktu_mulai_menunggu[id_tercatat]

    if status_sistem == "STANDBY" and ada_yang_menunggu_lama:
        status_sistem = "SAFE_TO_CROSS"
        waktu_aktif_hijau = time.time() 
        winsound.PlaySound("pelican.wav", winsound.SND_FILENAME | winsound.SND_ASYNC)
        
    if status_sistem == "SAFE_TO_CROSS":
        durasi_hijau = time.time() - waktu_aktif_hijau
        if durasi_hijau >= 15: 
            status_sistem = "STANDBY"

    #ui dashboard
    teks_x = int(w * 0.65)
    teks_y = int(h * 0.85)
    
    cv2.putText(gambar_final, f"TOTAL MOBIL: {total_mobil}", (teks_x+1, teks_y+1), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
    cv2.putText(gambar_final, f"TOTAL MOBIL: {total_mobil}", (teks_x, teks_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
    
    cv2.putText(gambar_final, f"TOTAL MOTOR: {total_motor}", (teks_x+1, teks_y + 26), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
    cv2.putText(gambar_final, f"TOTAL MOTOR: {total_motor}", (teks_x, teks_y + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 1)
    
    cv2.putText(gambar_final, f"TOTAL PENYEBERANG: {total_penyeberang}", (teks_x+1, teks_y + 51), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
    cv2.putText(gambar_final, f"TOTAL PENYEBERANG: {total_penyeberang}", (teks_x, teks_y + 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

    box_x1, box_y1 = w - 60, 75
    box_x2, box_y2 = w - 10, 175
    cv2.rectangle(gambar_final, (box_x1, box_y1), (box_x2, box_y2), (40, 40, 40), -1) 
    
    posisi_lampu_jalan = (w - 35, 100)
    posisi_lampu_mobil = (w - 35, 150)
    radius_lampu = 15

    if status_sistem == "STANDBY":
        cv2.circle(gambar_final, posisi_lampu_jalan, radius_lampu, (0, 0, 255), -1) 
        cv2.circle(gambar_final, posisi_lampu_mobil, radius_lampu, (0, 0, 0), -1) 
        cv2.putText(gambar_final, "STATUS: STANDBY", (10, h-20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    
    elif status_sistem == "SAFE_TO_CROSS":
        cv2.circle(gambar_final, posisi_lampu_jalan, radius_lampu, (0, 0, 0), -1) 
        cv2.circle(gambar_final, posisi_lampu_mobil, radius_lampu, (0, 255, 0), -1) 
        cv2.putText(gambar_final, "ALERT! KENDARAAN WAJIB BERHENTI", (10, h-20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

    cv2.imshow("SafeCross Prototype", gambar_final)
    
    key = cv2.waitKey(1) & 0xFF
    if key == ord('t'): 
        mode_thermal = not mode_thermal 
        print(f"Switching Mode... Thermal: {mode_thermal}")
    if key == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()