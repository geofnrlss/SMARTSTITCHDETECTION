import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import os
from datetime import datetime
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from tkcalendar import DateEntry
import mplcursors
import matplotlib.pyplot as plt
import gc
import cv2

# --- STYLE KONFIGURASI ---
BG_SIDEBAR, BG_MAIN, BG_CARD, BG_BORDER = "#F3F4F6", "#F9FAFB", "#FFFFFF", "#D1D5DB"
ACCENT, CLR_GOOD, CLR_BAD, CLR_RST, CLR_WARN = "#2563EB", "#10B981", "#EF4444", "#9CA3AF", "#F59E0B"
TXT_PRIMARY, TXT_SEC = "#1F2937", "#6B7280"

FONT_BOLD = ("Segoe UI", 10, "bold")
FONT_H1 = ("Segoe UI", 12, "bold")
FONT_DATA_BIG = ("Consolas", 20, "bold")
FONT_DATA_SMALL = ("Consolas", 10, "bold")
FONT_BTN_S = ("Segoe UI", 10, "bold")

class SmartStitchGUI:
    def __init__(self, root, num_cameras, camera_names, callbacks):
        self.root, self.num_cameras, self.camera_names, self.callbacks = root, num_cameras, camera_names, callbacks
        self.video_labels, self.status_labels = [], []
        self.good_labels, self.bad_labels, self.total_labels = [], [], []
        self.is_maximized = False
        self.is_graph_maximized = False 
        self.current_view = "CCTV"
        self.setup_ui()

    def setup_ui(self):
        self.root.configure(bg=BG_MAIN)
        sidebar = tk.Frame(self.root, bg=BG_SIDEBAR, width=220)
        sidebar.pack(side="left", fill="y"); sidebar.pack_propagate(False)
        
        # LOGO AREA
        self.logo_area = tk.Label(sidebar, bg=BG_SIDEBAR); self.logo_area.pack(pady=(20, 0))
        if os.path.exists("assets/SSD_white.ico"):
            try:
                img = Image.open("assets/SSD_white.ico").resize((100, 60), Image.LANCZOS)
                ph = ImageTk.PhotoImage(img); self.logo_area.config(image=ph); self.logo_area.image = ph
            except: pass
        
        tk.Label(sidebar, text="SMART STITCH\nDETECTION", font=FONT_BOLD, bg=BG_SIDEBAR, fg=ACCENT).pack(pady=10)
        
        btn_style = {"font": FONT_BTN_S, "relief": "flat", "pady": 12, "fg": "white", "cursor": "hand2"}
        tk.Button(sidebar, text="Monitoring CCTV", bg=ACCENT, command=self.show_cctv_view, **btn_style).pack(fill="x", padx=15, pady=5)
        tk.Button(sidebar, text="Dashboard Analytics", bg=CLR_WARN, command=lambda: self.show_analytics_view(), **btn_style).pack(fill="x", padx=15, pady=5)
        tk.Button(sidebar, text="Information Center", bg="#4B5563", command=self.show_info_view, **btn_style).pack(fill="x", padx=15, pady=5)
        tk.Button(sidebar, text="Back to Config", bg="#EF1818", command=self.callbacks['back'], **btn_style).pack(fill="x", padx=15, pady=5)
        tk.Button(sidebar, text="EXIT SYSTEM", bg=CLR_BAD, command=self.callbacks['exit'], **btn_style).pack(side="bottom", fill="x", padx=15, pady=20)
        # --- KOTAK INFO SHIFT & JAM (TARUH DI ATAS EXIT SYSTEM) ---
        info_box = tk.Frame(sidebar, bg="#E5E7EB", highlightthickness=1, highlightbackground=BG_BORDER, padx=10, pady=10)
        info_box.pack(side="bottom", fill="x", padx=15)

        self.sidebar_shift_lbl = tk.Label(info_box, text="Shift -", font=FONT_BOLD, bg="#E5E7EB", fg=ACCENT)
        self.sidebar_shift_lbl.pack()
        
        self.sidebar_date_lbl = tk.Label(info_box, text="00-00-0000", font=("Segoe UI", 9), bg="#E5E7EB", fg=TXT_PRIMARY)
        self.sidebar_date_lbl.pack()

        self.sidebar_time_lbl = tk.Label(info_box, text="00:00:00", font=("Consolas", 11, "bold"), bg="#E5E7EB", fg=TXT_PRIMARY)
        self.sidebar_time_lbl.pack()

        # Panggil fungsi jam pertama kali agar langsung jalan
        self.update_sidebar_clock()
        self.main_container = tk.Frame(self.root, bg=BG_MAIN); self.main_container.pack(side="right", fill="both", expand=True)
        self.show_cctv_view()

    def update_sidebar_clock(self):
        """Update informasi Shift, Tanggal, dan Jam secara real-time"""
        now = datetime.now()
        h = now.hour
        
        # Penentuan Shift sesuai jam operasional baru (07-15, 15-23, 23-07)
        if 7 <= h < 15:
            shift_text = "SHIFT 1 (PAGI)"
        elif 15 <= h < 23:
            shift_text = "SHIFT 2 (SORE)"
        else:
            shift_text = "SHIFT 3 (MALAM)"
            
        # Update teks ke label sidebar
        self.sidebar_shift_lbl.config(text=shift_text)
        self.sidebar_date_lbl.config(text=now.strftime("%d %B %Y"))
        self.sidebar_time_lbl.config(text=now.strftime("%H:%M:%S"))
        
        # Refresh setiap 1 detik
        self.root.after(1000, self.update_sidebar_clock)

    def show_cctv_view(self):
        self.current_view = "CCTV"
        plt.close('all'); gc.collect()
        for widget in self.main_container.winfo_children(): widget.destroy()
        self.cam_frame = tk.Frame(self.main_container, bg=BG_MAIN); self.cam_frame.pack(fill="both", expand=True, padx=10, pady=10)
        self.video_labels, self.status_labels, self.good_labels, self.bad_labels, self.total_labels = [], [], [], [], []
        
        for i in range(self.num_cameras):
            row, col = divmod(i, 2)
            card = tk.Frame(self.cam_frame, bg=BG_CARD, highlightthickness=1, highlightbackground=BG_BORDER)
            card.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")
            self.cam_frame.grid_columnconfigure(col, weight=1, uniform="c"); self.cam_frame.grid_rowconfigure(row, weight=1, uniform="r")
            
            header = tk.Frame(card, bg=BG_CARD); header.pack(fill="x", padx=12, pady=8)
            info_f = tk.Frame(header, bg=BG_CARD); info_f.pack(side="left")
            tk.Label(info_f, text=self.camera_names[i].upper(), font=FONT_BOLD, bg=BG_CARD, fg=ACCENT).pack(anchor="w")
            
            # Status Awal: Stopped
            status_lbl = tk.Label(info_f, text="● Stopped", font=("Segoe UI", 9, "bold"), bg=BG_CARD, fg="#9CA3AF")
            status_lbl.pack(anchor="w")
            
            tk.Button(header, text="⛶", font=("Segoe UI", 9, "bold"), bg="#E5E7EB", relief="flat", command=lambda x=i: self.toggle_maximize(x)).pack(side="right")
            
            footer = tk.Frame(card, bg=BG_CARD, pady=10); footer.pack(side="bottom", fill="x", padx=10)
            df = tk.Frame(footer, bg=BG_CARD); df.pack(side="left")
            gl = tk.Label(df, text="Good: 0", font=FONT_DATA_SMALL, fg=CLR_GOOD, bg=BG_CARD); gl.pack(side="left", padx=5)
            bl = tk.Label(df, text="Bad: 0", font=FONT_DATA_SMALL, fg=CLR_BAD, bg=BG_CARD); bl.pack(side="left", padx=5)
            tl = tk.Label(df, text="Total: 0", font=FONT_DATA_SMALL, fg=TXT_PRIMARY, bg=BG_CARD); tl.pack(side="left", padx=5)
            
            cf = tk.Frame(footer, bg=BG_CARD); cf.pack(side="right")
            # Trigger "Connecting" saat Start diklik
            tk.Button(cf, text="▶ START", bg=CLR_GOOD, fg="white", font=FONT_BTN_S, 
                      command=lambda x=i: [self.status_labels[x].config(text="● Connecting", fg=CLR_WARN), self.callbacks['start'](x)], 
                      relief="flat").pack(side="left", padx=2)
            tk.Button(cf, text="■ STOP", bg=CLR_BAD, fg="white", font=FONT_BTN_S, command=lambda x=i: self.callbacks['stop'](x), relief="flat").pack(side="left", padx=2)
            tk.Button(cf, text="↺ RESET", bg=CLR_RST, fg="white", font=FONT_BTN_S, command=lambda x=i: self.callbacks['reset'](x), relief="flat").pack(side="left", padx=2)
            
            video_lbl = tk.Label(card, bg="black", text="NO STREAM\nPRESS START", fg="white"); video_lbl.pack(fill="both", expand=True, padx=10, pady=2)
            
            self.video_labels.append(video_lbl); self.status_labels.append(status_lbl); self.good_labels.append(gl); self.bad_labels.append(bl); self.total_labels.append(tl)

    def show_analytics_view(self, selected_date=None, selected_shift=None):
        self.current_view = "ANALYTICS"
        plt.close('all'); gc.collect()
        for widget in self.main_container.winfo_children(): widget.destroy()
        all_data = self.callbacks['get_shift_data']()
        self.current_shift_data, self.current_line_names, self.current_line_data = all_data["shift"], all_data["line_names"], all_data["lines"]
        
        container = tk.Frame(self.main_container, bg=BG_MAIN); container.pack(fill="both", expand=True, padx=30, pady=15)
        
        hf = tk.Frame(container, bg=BG_MAIN); hf.pack(fill="x", pady=(0, 10))
        tk.Label(hf, text="PRODUCTION ANALYTICS CENTER", font=FONT_H1, bg=BG_MAIN, fg=ACCENT).pack(side="left")
        sf = tk.Frame(hf, bg=BG_MAIN); sf.pack(side="right")
        cal = DateEntry(sf, width=12, background='darkblue', foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd')
        if selected_date: cal.set_date(datetime.strptime(selected_date, '%Y-%m-%d'))
        cal.pack(side="left", padx=5)
        cb_shift = ttk.Combobox(sf, values=["Shift 1", "Shift 2", "Shift 3", "Full Day"], width=10, state="readonly")
        cb_shift.set(selected_shift if selected_shift else "Shift 2"); cb_shift.pack(side="left", padx=5)
        tk.Button(sf, text="LOAD DATA", bg=ACCENT, fg="white", font=FONT_BTN_S, relief="flat", padx=15, command=lambda: self.callbacks['load_data'](cal.get_date().strftime('%Y-%m-%d'), cb_shift.get())).pack(side="left", padx=5)

        tf = tk.Frame(container, bg=BG_MAIN); tf.pack(fill="x", pady=5)
        tk.Label(tf, text="Line Filters:", font=FONT_BOLD, bg=BG_MAIN, fg=TXT_SEC).pack(side="left", padx=(10, 10))
        self.line_vars = {}
        for name in self.current_line_names:
            var = tk.BooleanVar(value=True); self.line_vars[name] = var
            tk.Checkbutton(tf, text=name, variable=var, font=FONT_BTN_S, bg=BG_CARD, indicatoron=False, selectcolor=ACCENT, fg=TXT_PRIMARY, padx=10, command=lambda: self.refresh_analytics_chart(cb_shift.get())).pack(side="left", padx=5)

        # Simpan reference labels untuk update dinamis
        card_container = tk.Frame(container, bg=BG_MAIN); card_container.pack(fill="x", pady=5)
        self.stat_labels = {} 
        stats_cfg = [("TOTAL PRODUCTION", TXT_PRIMARY, "total"), ("TOTAL GOOD BAG", CLR_GOOD, "good"), ("TOTAL BAD BAG", CLR_BAD, "bad")]
        for label_text, color, key in stats_cfg:
            box = tk.Frame(card_container, bg=BG_CARD, highlightthickness=1, highlightbackground=BG_BORDER, padx=20, pady=15); box.pack(side="left", expand=True, fill="both", padx=8)
            tk.Label(box, text=label_text, font=FONT_BOLD, bg=BG_CARD, fg=TXT_SEC).pack(anchor="w")
            val_lbl = tk.Label(box, text="-", font=FONT_DATA_BIG, bg=BG_CARD, fg=color)
            val_lbl.pack(anchor="w")
            self.stat_labels[key] = val_lbl

        self.graph_container = tk.Frame(container, bg=BG_MAIN); self.graph_container.pack(fill="both", expand=True, pady=10)
        self.current_cb_shift = cb_shift 
        self.refresh_analytics_chart(cb_shift.get())
        tk.Button(container, text="GENERATE OFFICIAL EXCEL REPORT (.XLSX)", command=self.callbacks['export'], bg=CLR_GOOD, fg="white", font=FONT_BOLD, pady=12, relief="flat").pack(fill="x", pady=10)

    def show_info_view(self):
        self.current_view = "INFO"
        plt.close('all'); gc.collect() 
        for widget in self.main_container.winfo_children(): widget.destroy()
        
        outer_container = tk.Frame(self.main_container, bg=BG_MAIN)
        outer_container.place(relx=0.5, rely=0.5, anchor="center") 

        tk.Label(outer_container, text="CAMERA ALIGNMENT INFORMATION", font=FONT_H1, bg=BG_MAIN, fg=ACCENT).pack(pady=(0, 30))
        img_frame = tk.Frame(outer_container, bg=BG_MAIN); img_frame.pack(fill="x", expand=True)
        
        def create_guide_card(parent, title, color, img_path, note_text):
            card = tk.Frame(parent, bg=BG_CARD, highlightthickness=2, highlightbackground=color)
            card.pack(side="left", padx=20, anchor="n") 
            header = tk.Frame(card, bg=color, pady=10); header.pack(fill="x")
            tk.Label(header, text=title, font=FONT_BOLD, fg="white", bg=color).pack()
            
            body = tk.Frame(card, bg=BG_CARD); body.pack(fill="both", expand=True, padx=15, pady=15)
            display_lbl = tk.Label(body, bg=BG_CARD); display_lbl.pack()
            
            if os.path.exists(img_path):
                try:
                    raw_img = Image.open(img_path)
                    tw = 500; th = int((tw / raw_img.size[0]) * raw_img.size[1])
                    render = ImageTk.PhotoImage(raw_img.resize((tw, th), Image.LANCZOS))
                    display_lbl.config(image=render, width=tw, height=th); display_lbl.image = render 
                except: display_lbl.config(text="ERROR LOAD IMAGE", fg=CLR_BAD)

            desc_container = tk.Frame(body, bg=BG_CARD)
            desc_container.pack(fill="x", pady=(15, 0))
            tk.Label(desc_container, text="CATATAN:", font=FONT_BOLD, fg=TXT_PRIMARY, bg=BG_CARD).pack(anchor="w")
            tk.Label(desc_container, text=note_text, font=("Segoe UI", 10), fg=TXT_PRIMARY, bg=BG_CARD, justify="left", anchor="w", wraplength=480).pack(fill="x")
            return card

        note_benar = "• Kamera tegak lurus dengan conveyor\n• Garis kuning membagi area karung secara simetris"
        note_salah = "• Kamera atau sudut pandang miring\n• Visual jahitan tertutup oleh komponen mesin"
        
        create_guide_card(img_frame, "CORRECT CAMERA ALIGNMENT", CLR_GOOD, "assets/goodcamera.png", note_benar)
        create_guide_card(img_frame, "INCORRECT CAMERA ALIGNMENT", CLR_BAD, "assets/badcamera.png", note_salah)
        
        footer_warn = tk.Frame(outer_container, bg="#FEF2F2", highlightthickness=1, highlightbackground=CLR_BAD, pady=20)
        footer_warn.pack(fill="x", padx=20, pady=(40, 0)) 
        tk.Label(footer_warn, text="⚠ PEMBERITAHUAN PENTING", font=FONT_BOLD, fg=CLR_BAD, bg="#FEF2F2").pack()
        tk.Label(footer_warn, text="Segera lapor ke Bagian Teknisi jika terdapat posisi kamera yang tidak sesuai di lapangan.", font=("Segoe UI", 11), fg=TXT_PRIMARY, bg="#FEF2F2").pack(pady=5)
        
    def refresh_analytics_chart(self, shift_name):
        # Update Stats Dinamis (Atas)
        f_tg, f_tb = 0, 0
        for name in self.current_line_names:
            if self.line_vars[name].get():
                f_tg += sum(self.current_shift_data["per_line_good"].get(name, [0]))
                f_tb += sum(self.current_shift_data["per_line_bad"].get(name, [0]))
        
        total_p = f_tg + f_tb
        div = total_p if total_p > 0 else 1
        self.stat_labels["total"].config(text=f"{total_p} Bags")
        self.stat_labels["good"].config(text=f"{f_tg} ({(f_tg/div)*100:.1f}%)")
        self.stat_labels["bad"].config(text=f"{f_tb} ({(f_tb/div)*100:.1f}%)")

        for widget in self.graph_container.winfo_children(): widget.destroy()
        left_box = tk.Frame(self.graph_container, bg=BG_CARD, highlightthickness=1, highlightbackground=BG_BORDER); left_box.pack(side="left", fill="both", expand=True, padx=(0, 8) if not self.is_graph_maximized else 0)
        tk.Label(left_box, text="Hourly Productivity Trend", font=FONT_BOLD, bg=BG_CARD, fg="black").pack(pady=10)
        zoom_icon = "⛶" if not self.is_graph_maximized else "⧉" 
        tk.Button(left_box, text=zoom_icon, font=FONT_BTN_S, bg="#E5E7EB", relief="flat", command=self.toggle_graph_maximize).place(relx=0.98, rely=0.02, anchor="ne")

        fig_l = Figure(figsize=(5, 4.5), dpi=95); ax1 = fig_l.add_subplot(111)
        hrs = self.current_shift_data.get("labels", [])
        clrs = ['#2563EB', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899', '#06B6D4', '#F97316']
        
        # Buat variabel penanda apakah ada line yang di-plot
        has_plots = False 
        
        if "per_line_good" in self.current_shift_data:
            for i, name in enumerate(self.current_line_names):
                if self.line_vars.get(name) and self.line_vars[name].get():
                    data_y = self.current_shift_data["per_line_good"].get(name, [])
                    if len(hrs) == len(data_y) and len(hrs) > 0:
                        ax1.plot(hrs, data_y, marker='o', label=name, color=clrs[i % len(clrs)], linewidth=2)
                        has_plots = True # Tandai True karena ada line yang digambar

        ax1.set_xlabel("Jam Operasional"); ax1.set_ylabel("Bag")
        if has_plots: ax1.legend(loc='upper right', fontsize=8)
        
        canvas_l = FigureCanvasTkAgg(fig_l, master=left_box)
        canvas_l.draw()
        canvas_l.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)

        if not self.is_graph_maximized:
            right_box = tk.Frame(self.graph_container, bg=BG_CARD, highlightthickness=1, highlightbackground=BG_BORDER); right_box.pack(side="right", fill="both", expand=True, padx=(8, 0))
            fig_r = Figure(figsize=(5, 2.5), dpi=95); ax2 = fig_r.add_subplot(111)
            bars = ax2.bar(['Good', 'Bad'], [f_tg, f_tb], color=[CLR_GOOD, CLR_BAD], alpha=0.7, width=0.5)
            ax2.bar_label(bars, padding=3, fontweight='bold', fontsize=10)
            max_v = max(f_tg, f_tb); ax2.set_ylim(0, max_v * 1.4 if max_v > 0 else 10)
            ax2.set_title(f"Quality Summary ({shift_name})", fontdict={'fontsize': 10, 'fontweight': 'bold'})
            canvas_r = FigureCanvasTkAgg(fig_r, master=right_box); canvas_r.draw(); canvas_r.get_tk_widget().pack(fill="x", padx=5)

            # Tabel Tetap Menampilkan Semua Line (Stay)
            tk.Label(right_box, text="Detailed Production per Line", font=FONT_BOLD, bg=BG_CARD, fg="black").pack(pady=5)
            style = ttk.Style(); style.theme_use('clam')
            style.configure("Treeview.Heading", background=ACCENT, foreground="white", font=FONT_BOLD)
            style.configure("Treeview", font=("Segoe UI", 10, "normal"), rowheight=25, background="white")
            tree = ttk.Treeview(right_box, columns=("Line", "Good", "Bad", "Total"), show='headings', height=self.num_cameras)
            for col in ("Line", "Good", "Bad", "Total"): tree.heading(col, text=col); tree.column(col, width=70, anchor="center")
            
            for i in range(self.num_cameras):
                n = self.camera_names[i]
                g, b = self.current_line_data[i]["Good_Stitch"], self.current_line_data[i]["Bad_Stitch"]
                tree.insert("", "end", values=(n, g, b, g + b))
            tree.pack(fill="both", expand=True, padx=15, pady=10)
        try: mplcursors.cursor(ax1, hover=True).connect("add", lambda sel: sel.annotation.set_text(f"{sel.artist.get_label()}: {int(sel.target[1])} Bags"))
        except: pass

    def toggle_graph_maximize(self): self.is_graph_maximized = not self.is_graph_maximized; self.refresh_analytics_chart(self.current_cb_shift.get())
    def toggle_maximize(self, index):
        if not self.is_maximized:
            for i, video in enumerate(self.video_labels):
                if i != index: video.master.grid_remove()
                else: video.master.grid(row=0, column=0, columnspan=2, rowspan=3, sticky="nsew")
            self.is_maximized = True
        else: self.show_cctv_view(); self.is_maximized = False
    def update_view(self, threads, counts):
        if self.current_view != "CCTV": return
        for i in range(self.num_cameras):
            t = threads[i]
            if not t:
                self.status_labels[i].config(text="● Stopped", fg="#9CA3AF")
                self.video_labels[i].config(image="", text="NO STREAM")
            else:
                if t.status == "Live" and t.latest_frame is not None:
                    w = self.video_labels[i].winfo_width()
                    h = self.video_labels[i].winfo_height()
                    if w < 10 or h < 10:
                        w, h = 400, 250
                    
                    # Gunakan cv2.resize yang jauh lebih cepat daripada Image.LANCZOS untuk menghindari lag GUI
                    resized_frame = cv2.resize(t.latest_frame, (w, h), interpolation=cv2.INTER_LINEAR)
                    img = Image.fromarray(resized_frame)
                    tk_img = ImageTk.PhotoImage(image=img)
                    
                    self.video_labels[i].config(image=tk_img, text=""); self.video_labels[i].image = tk_img
                    self.status_labels[i].config(text="● Live", fg=CLR_GOOD)
                elif t.status == "Connecting": self.status_labels[i].config(text="● Connecting", fg=CLR_WARN)
                elif t.status == "Offline": self.status_labels[i].config(text="● Offline", fg="#6B7280")
                elif t.status == "Error": self.status_labels[i].config(text="● Error", fg=CLR_BAD)
            g, b = counts[i]['Good_Stitch'], counts[i]['Bad_Stitch']
            self.good_labels[i].config(text=f"Good: {g}"); self.bad_labels[i].config(text=f"Bad: {b}"); self.total_labels[i].config(text=f"Total: {g+b}")