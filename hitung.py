import cv2
import time
import os  # <--- [TAMBAHAN BARU 1] Library bawaan untuk memanggil sistem Mac

# 1. Panggil AI YOLOv8
print("Memuat AI Pelican Crossing...")
from ultralytics import YOLO
model = YOLO('yolov8n.pt') 

# 2. Input Kamera (0 untuk Webcam)
cap = cv2.VideoCapture(0) 

# Pengaturan Zona & Waktu
zona_y = [200, 300, 500, 600] # [X_kiri, Y_atas, X_kanan, Y_bawah]
detik_minimal_menunggu = 5

# Variabel Logika Sistem
waktu_mulai_menunggu = {} 
status_sistem = "STANDBY"
waktu_aktif_hijau = 0 

print(f"Sistem Smart Pelican Crossing Berjalan... Tekan 'q' untuk keluar.")

while True:
    berhasil, frame = cap.read()
    if not berhasil:
        break
        
    gambar_final = frame.copy()
    h, w, _ = frame.shape

    # 3. Jalankan AI Tracker (Fokus Orang)
    hasil_deteksi = model.track(frame, persist=True, classes=[0], verbose=False)
    
    # 4. Gambar "Zona Menunggu"
    x1z, y1z, x2z, y2z = zona_y
    cv2.rectangle(gambar_final, (x1z, y1z), (x2z, y2z), (255, 0, 0), 3) 
    cv2.putText(gambar_final, "AREA MENUNGGU", (x1z, y1z-10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2)

    ada_yang_menunggu_lama = False
    track_ids_frame_ini = []

    if hasil_deteksi[0].boxes.id is not None:
        boxes = hasil_deteksi[0].boxes.xyxy.cpu().numpy() 
        track_ids = hasil_deteksi[0].boxes.id.cpu().numpy()

        for box, track_id in zip(boxes, track_ids):
            px1, py1, px2, py2 = box
            cx = int((px1 + px2) / 2)
            cy = int((py1 + py2) / 2) 

            # Cek apakah orang ada di dalam zona biru
            di_dalam_zona = (x1z < cx < x2z) and (y1z < cy < y2z)
            
            warna_titik = (0, 0, 255) 
            if di_dalam_zona:
                warna_titik = (0, 255, 0) 
                track_ids_frame_ini.append(track_id)

                if track_id not in waktu_mulai_menunggu:
                    waktu_mulai_menunggu[track_id] = time.time()
                
                durasi_menunggu = time.time() - waktu_mulai_menunggu[track_id]
                
                cv2.putText(gambar_final, f"Mtr: {durasi_menunggu:.1f}s", (int(px1), int(py1)-10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

                if durasi_menunggu >= detik_minimal_menunggu:
                    ada_yang_menunggu_lama = True

            cv2.circle(gambar_final, (cx, cy), 5, warna_titik, -1)

    for id_tercatat in list(waktu_mulai_menunggu.keys()):
        if id_tercatat not in track_ids_frame_ini:
            del waktu_mulai_menunggu[id_tercatat]

    # ==========================================
    # 8. SISTEM IOT & TRIGGER SUARA
    # ==========================================
    if status_sistem == "STANDBY" and ada_yang_menunggu_lama:
        status_sistem = "SAFE_TO_CROSS"
        waktu_aktif_hijau = time.time() 
        
        # [TAMBAHAN BARU 2] EKSEKUSI SUARA DI MACBOOK-MU!
        # Tanda '&' di paling belakang SANGAT PENTING agar videomu tidak nge-lag saat suara diputar!
        print("MENGELUARKAN SUARA SIRINE!")
        
        # Opsi A: Menggunakan Suara Robot Bawaan Mac
        os.system("say -v Damayanti 'Ayoo  kendaraan berhenti stop woy. Kendaraan diharap berhenti.' &")
        
        # Opsi B: JIKA KAMU PUNYA FILE MP3 (misal namanya 'sirine.mp3' di folder yang sama)
        # Hapus tanda '#' di bawah ini, dan beri '#' pada Opsi A di atas
        # os.system("afplay sirine.mp3 &")

    # Waktu Lampu Hijau (mati setelah 15 detik)
    if status_sistem == "SAFE_TO_CROSS":
        durasi_hijau = time.time() - waktu_aktif_hijau
        if durasi_hijau >= 15: 
            status_sistem = "STANDBY"

    # Gambar Lampu Virtual
    cv2.rectangle(gambar_final, (w-200, 20), (w-20, 220), (50, 50, 50), -1) 
    posisi_lampu_jalan = (w-110, 70)
    posisi_lampu_mobil = (w-110, 170)

    if status_sistem == "STANDBY":
        cv2.circle(gambar_final, posisi_lampu_jalan, 40, (0, 0, 255), -1) 
        cv2.circle(gambar_final, posisi_lampu_mobil, 40, (0, 100, 0), -1) 
        cv2.putText(gambar_final, "STATUS: STANDBY", (10, h-20), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    
    elif status_sistem == "SAFE_TO_CROSS":
        cv2.circle(gambar_final, posisi_lampu_jalan, 40, (0, 255, 0), -1) 
        cv2.circle(gambar_final, posisi_lampu_mobil, 40, (0, 0, 255), -1) 
        cv2.putText(gambar_final, "ALERT! SIRINE AKTIF!", (10, h-60), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 4)
        cv2.putText(gambar_final, "KENDARAAN WAJIB BERHENTI", (10, h-20), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

    cv2.imshow("Smart Pelican Crossing Prototype", gambar_final)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()