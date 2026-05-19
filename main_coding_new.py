import os
import sys
import threading
import multiprocessing as mp
import json
import time
import pandas as pd
from datetime import datetime, timedelta
from tkinter import messagebox
import tkinter as tk
import cv2
from PIL import Image, ImageTk
import subprocess
import gc
import torch
import numpy as np
from ultralytics import YOLO 
from sort import Sort

from GUI_LAYOUT import SmartStitchGUI

# --- KONFIGURASI ---
EXPORT_FOLDER = "export_excel"      
CONFIG_FILE   = "camera_config.json" 
MODEL_PATH    = "best.pt"  
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|stimeout;5000000|max_delay;5000000"

if not os.path.exists(EXPORT_FOLDER):
    os.makedirs(EXPORT_FOLDER)

# --- WORKER MULTIPROCESSING ---
def camera_worker(index, address, camera_name, queue_out, stop_ev, reset_ev):
    import cv2
    import torch
    import numpy as np
    import time
    from ultralytics import YOLO
    from sort import Sort
    import threading

    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    try:
        model = YOLO("best.pt")
        model.to(device)
    except Exception as e:
        queue_out.put(("Error", None, 0, 0))
        return
        
    tracker = Sort(max_age=20, min_hits=1, iou_threshold=0.1)
    track_history = {}
    last_count_time = 0
    
    good_count = 0
    bad_count = 0
    
    cap = cv2.VideoCapture(str(address), cv2.CAP_FFMPEG)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 2)
    if not cap.isOpened():
        queue_out.put(("Error", None, 0, 0))
        return
        
    grabber_running = True
    current_raw_frame = [None]
    
    def grab_frames():
        nonlocal cap
        failed_reads = 0
        while grabber_running and not stop_ev.is_set():
            if cap is None or not cap.isOpened():
                failed_reads += 1
            else:
                try:
                    ret, f = cap.read()
                    if ret:
                        current_raw_frame[0] = f
                        failed_reads = 0
                    else:
                        failed_reads += 1
                except Exception as e:
                    print(f"Read error {camera_name}: {e}")
                    failed_reads += 1

            if failed_reads > 100:  # ~1-2 detik tidak ada frame masuk
                print(f"[{camera_name}] Connection lost. Reconnecting...")
                try:
                    while not queue_out.empty():
                        queue_out.get_nowait()
                    queue_out.put_nowait(("Connecting", None, good_count, bad_count))
                except: pass
                
                if cap is not None:
                    try: cap.release()
                    except: pass
                time.sleep(2)
                try:
                    cap = cv2.VideoCapture(str(address), cv2.CAP_FFMPEG)
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 2)
                except: pass
                failed_reads = 0
            elif failed_reads > 0:
                time.sleep(0.01)
                
    threading.Thread(target=grab_frames, daemon=True).start()
    
    queue_out.put(("Connecting", None, 0, 0))
    
    try:
        while not stop_ev.is_set():
            if reset_ev.is_set():
                good_count = 0
                bad_count = 0
                track_history.clear()
                reset_ev.clear()
                
            if current_raw_frame[0] is None:
                time.sleep(0.01)
                continue
                
            frame = current_raw_frame[0].copy()
            current_raw_frame[0] = None
            
            h, w, _ = frame.shape
            line_x = w // 2
            
            results = model.predict(frame, imgsz=480, verbose=False)
            
            detections, class_list = [], []
            for box in results[0].boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                score = float(box.conf)
                class_name = model.names[int(box.cls)]
                if score > 0.4:
                    detections.append([x1, y1, x2, y2, score])
                    class_list.append(class_name)
                    
            tracks = tracker.update(np.array(detections)) if detections else np.empty((0, 5))
            
            for *box_coord, tid in tracks.astype(int):
                x1, y1, x2, y2 = box_coord
                track_id = int(tid)
                
                cls_name = next((c for b, c in zip(detections, class_list) if abs(((b[0] + b[2]) // 2) - ((x1 + x2) // 2)) < 30), None)
                if not cls_name: continue
                    
                cx = int((x1 + x2) / 2)
                cy = int((y1 + y2) / 2)
                
                is_bad = 'bad' in cls_name.lower()
                color = (0, 0, 255) if is_bad else (0, 255, 0)
                label = "Bad Stitch" if is_bad else "Good Stitch"
                
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.circle(frame, (cx, cy), 4, color, -1)
                cv2.putText(frame, f"{label} ID: {track_id}", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                
                if track_id not in track_history:
                    track_history[track_id] = {'classes': [], 'prev_cx': cx, 'counted': False}
                    
                history = track_history[track_id]
                history['classes'].append(is_bad)
                prev_cx = history['prev_cx']
                
                crossed = (prev_cx < line_x <= cx) or (prev_cx > line_x >= cx)
                
                if crossed and not history['counted']:
                    history['counted'] = True
                    current_time = time.time()
                    if (current_time - last_count_time) >= 1.5:
                        last_count_time = current_time
                        bad_det_count = sum(1 for b in history['classes'] if b)
                        good_det_count = len(history['classes']) - bad_det_count
                        
                        if bad_det_count > good_det_count:
                            bad_count += 1
                        else:
                            good_count += 1
                            
                history['prev_cx'] = cx

            cv2.line(frame, (line_x, 0), (line_x, h), (0, 255, 255), 3)
            cv2.putText(frame, "GARIS PENGHITUNGAN", (line_x + 10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2, cv2.LINE_AA)
            
            # Agar memori queue tidak bocor / menumpuk, resize ke format RGB (OpenCV pakai BGR)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Drop old frames jika GUI belum membacanya (agar tidak lag)
            while not queue_out.empty():
                try: queue_out.get_nowait()
                except: break
                
            try: queue_out.put_nowait(("Live", rgb_frame, good_count, bad_count))
            except: pass
                
    except Exception as e:
        print(f"Error pada Camera {camera_name}: {e}")
        try: queue_out.put_nowait(("Error", None, good_count, bad_count))
        except: pass
    finally:
        grabber_running = False
        cap.release()
        try: queue_out.put_nowait(("Offline", None, good_count, bad_count))
        except: pass


# Adapter agar kompatibel dengan GUI lama
class DummyThreadAdapter:
    def __init__(self):
        self.status = "Offline"
        self.latest_frame = None


class SmartStitchEngine:
    def __init__(self):
        self.root = tk.Tk()
        self.root.state('zoomed')
        self.root.title("SMART STITCH DETECTION - PT PETROKIMIA GRESIK")
        self.last_saved_hour = datetime.now().hour
        
        try:
            with open(CONFIG_FILE, 'r') as f:
                cfg = json.load(f).get('active_config', {})
                self.addrs, self.names = cfg.get('addresses', []), cfg.get('names', [])
        except: 
            messagebox.showerror("Error", "Config Missing!"); sys.exit()

        self.num = len(self.addrs)
        
        # --- MULTIPROCESSING COMPONENTS ---
        self.processes = [None] * self.num
        self.queues = [None] * self.num
        self.stop_events = [None] * self.num
        self.reset_events = [None] * self.num
        self.dummy_threads = [DummyThreadAdapter() for _ in range(self.num)]
        
        self.global_counts = [{"Good_Stitch": 0, "Bad_Stitch": 0} for _ in range(self.num)]
        self.last_hour_counts = [{"Good_Stitch": 0, "Bad_Stitch": 0} for _ in range(self.num)]

        self.hourly_chart_data = {"good": [], "bad": [], "labels": [], "per_line_good": {}, "per_line_bad": {}}
        self.lines_data_for_gui = [{"Good_Stitch": 0, "Bad_Stitch": 0} for _ in range(self.num)]
        
        callbacks = {
            'start': self.start_cam, 'stop': self.stop_cam, 'reset': self.reset_cam,
            'export': self.manual_export, 'back': self.back_to_config,
            'get_shift_data': self.get_current_data, 'load_data': self.load_historical_data, 
            'exit': self.shutdown
        }
        
        self.gui = SmartStitchGUI(self.root, self.num, self.names, callbacks)
        self.update_loop()
        
        # Auto-start semua kamera
        for i in range(self.num): 
            self.start_cam(i)
            
        self.root.mainloop()

    def get_current_data(self):
        return {
            "shift": self.hourly_chart_data, 
            "lines": self.lines_data_for_gui if self.gui.current_view == "ANALYTICS" else self.global_counts, 
            "line_names": self.names
        }

    def get_production_date(self):
        now = datetime.now()
        if now.hour < 7:
            return (now - timedelta(days=1)).strftime('%Y-%m-%d')
        else:
            return now.strftime('%Y-%m-%d')

    def auto_reset_all_counts(self):
        for i in range(self.num):
            self.reset_cam(i)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Auto-Reset Shift Berhasil.")

    def auto_export_shift_xlsx(self, shift_tag, shift_code, prod_date):
        try:
            self.load_historical_data(prod_date, shift_code, is_auto=True)
            export_data = {"Jam": self.hourly_chart_data["labels"]}
            for name in self.names:
                export_data[f"{name}_Good"] = self.hourly_chart_data["per_line_good"][name]
                export_data[f"{name}_Bad"] = self.hourly_chart_data["per_line_bad"][name]
            
            df = pd.DataFrame(export_data)
            filename = f"AUTO_REPORT_{shift_tag}_{prod_date}.xlsx"
            fpath = os.path.join(EXPORT_FOLDER, filename)
            df.to_excel(fpath, index=False, engine='openpyxl')
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Auto-Export Berhasil: {filename}")
        except Exception as e:
            print(f"Gagal Export: {e}")

    def update_loop(self):
        now = datetime.now()
        prod_date = self.get_production_date()
        
        if now.hour != self.last_saved_hour:
            self.save_hourly_log(self.last_saved_hour)
            if now.hour == 14: self.auto_export_shift_xlsx("SHIFT_1_PAGI", "Shift 1", prod_date)
            elif now.hour == 22: self.auto_export_shift_xlsx("SHIFT_2_SORE", "Shift 2", prod_date)
            elif now.hour == 6: self.auto_export_shift_xlsx("SHIFT_3_MALAM", "Shift 3", prod_date)

            if now.hour in [7, 15, 23]:
                self.auto_reset_all_counts()
            self.last_saved_hour = now.hour

        # Ambil data terbaru dari antrean Multiprocessing Queue
        for i in range(self.num):
            if self.processes[i] is not None and self.queues[i] is not None:
                latest_data = None
                while not self.queues[i].empty():
                    try: latest_data = self.queues[i].get_nowait()
                    except: break
                
                if latest_data:
                    status, frame, good, bad = latest_data
                    self.dummy_threads[i].status = status
                    self.dummy_threads[i].latest_frame = frame
                    self.global_counts[i]["Good_Stitch"] = good
                    self.global_counts[i]["Bad_Stitch"] = bad

        if self.gui.current_view == "CCTV":
            self.gui.update_view(self.dummy_threads, self.global_counts)
            
        self.root.after(33, self.update_loop)

    def load_historical_data(self, date_str, shift_selected, is_auto=False):
        f_path = os.path.join(EXPORT_FOLDER, f"hourly_log_{date_str}.csv")
        try:
            if not os.path.exists(f_path):
                if not is_auto: messagebox.showwarning("Info", "Data produksi belum tersedia.")
                return

            df_all = pd.read_csv(f_path)
            if shift_selected == "Shift 1": h_range = [7, 8, 9, 10, 11, 12, 13, 14]
            elif shift_selected == "Shift 2": h_range = [15, 16, 17, 18, 19, 20, 21, 22]
            elif shift_selected == "Shift 3": h_range = [23, 0, 1, 2, 3, 4, 5, 6]
            else: h_range = [7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,0,1,2,3,4,5,6]

            df_shift = df_all[df_all['Jam'].isin(h_range)].copy()
            df_shift['Jam'] = pd.Categorical(df_shift['Jam'], categories=h_range, ordered=True)
            df_shift = df_shift.sort_values('Jam')

            self.hourly_chart_data["labels"] = [f"{int(h):02d}" for h in df_shift["Jam"].tolist()]
            self.hourly_chart_data["per_line_good"], self.hourly_chart_data["per_line_bad"] = {}, {}
            self.hourly_chart_data["good"], self.hourly_chart_data["bad"] = [], []
            
            csv_cols = {c.upper().strip(): c for c in df_shift.columns}
            new_table = []
            for name in self.names:
                n_up = name.upper().strip()
                col_g, col_b = csv_cols.get(f"{n_up}_GOOD"), csv_cols.get(f"{n_up}_BAD")
                g_vals = df_shift[col_g].fillna(0).tolist() if col_g else [0]*len(df_shift)
                b_vals = df_shift[col_b].fillna(0).tolist() if col_b else [0]*len(df_shift)
                self.hourly_chart_data["per_line_good"][name] = g_vals
                self.hourly_chart_data["per_line_bad"][name] = b_vals 
                self.hourly_chart_data["good"].append(sum(g_vals)); self.hourly_chart_data["bad"].append(sum(b_vals))
                new_table.append({"Good_Stitch": sum(g_vals), "Bad_Stitch": sum(b_vals)})
            
            self.lines_data_for_gui = new_table
            if not is_auto: self.gui.show_analytics_view(date_str, shift_selected)
        except Exception as e: print(f"Error load data: {e}")
            
    def save_hourly_log(self, h):
        date_str = self.get_production_date()
        fpath = os.path.join(EXPORT_FOLDER, f"hourly_log_{date_str}.csv")
        new_entry = {"Jam": h}
        for i, name in enumerate(self.names):
            new_entry[f"{name}_Good"] = max(0, self.global_counts[i]["Good_Stitch"] - self.last_hour_counts[i]["Good_Stitch"])
            new_entry[f"{name}_Bad"] = max(0, self.global_counts[i]["Bad_Stitch"] - self.last_hour_counts[i]["Bad_Stitch"])
            self.last_hour_counts[i] = self.global_counts[i].copy()
        pd.DataFrame([new_entry]).to_csv(fpath, mode='a', index=False, header=not os.path.exists(fpath))

    def start_cam(self, i):
        if self.processes[i] is None:
            self.queues[i] = mp.Queue(maxsize=3)
            self.stop_events[i] = mp.Event()
            self.reset_events[i] = mp.Event()
            
            p = mp.Process(target=camera_worker, args=(i, self.addrs[i], self.names[i], self.queues[i], self.stop_events[i], self.reset_events[i]))
            p.daemon = True
            p.start()
            self.processes[i] = p
            self.dummy_threads[i].status = "Connecting"

    def stop_cam(self, i): 
        if self.processes[i]:
            self.stop_events[i].set()
            self.processes[i].join(timeout=1.5)
            self.processes[i] = None
            self.dummy_threads[i].status = "Offline"
            self.dummy_threads[i].latest_frame = None

    def reset_cam(self, i): 
        if self.processes[i]:
            self.reset_events[i].set()
        self.global_counts[i] = {"Good_Stitch": 0, "Bad_Stitch": 0}
        self.last_hour_counts[i] = {"Good_Stitch": 0, "Bad_Stitch": 0}
        
    def manual_export(self):
        messagebox.showinfo("Export", f"Laporan manual XLSX telah disimpan untuk hari produksi {self.get_production_date()}.")
        
    def back_to_config(self): 
        self.shutdown()
        subprocess.Popen([sys.executable, 'camera_config_new.py'])
        
    def shutdown(self):
        for i in range(self.num):
            self.stop_cam(i)
        self.root.destroy()


if __name__ == "__main__":
    mp.freeze_support() # Wajib untuk Windows multiprocessing
    SmartStitchEngine()