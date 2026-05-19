import os, sys, json, subprocess
import tkinter as tk
import customtkinter as ctk 
from tkinter import messagebox, ttk
from PIL import Image, ImageTk, ImageEnhance
from pathlib import Path

# --- AUTO VENV CHECK ---
base_dir = os.path.dirname(os.path.abspath(__file__))
venv_py = os.path.join(base_dir, "venv", "Scripts", "python.exe")
if os.path.exists(venv_py) and os.path.normcase(sys.executable) != os.path.normcase(venv_py):
    os.execv(venv_py, [venv_py] + sys.argv)

# --- CONFIGURATION ---
COLOR_PRIMARY, COLOR_ACCENT, COLOR_BG_OUT, COLOR_CARD = "#183BC8", "#E0E7FF", "#EDF2F7", "#FFFFFF"
TXT_DARK, TXT_SEC = "#1F2937", "#6B7280"
CONFIG_FILE, DEFAULT_RTSP = "camera_config.json", "/Streaming/Channels/201"
ASSETS_PATH = Path(__file__).parent

ctk.set_appearance_mode("light") 

current_step = 1
rows_data = []

# --- CLASS BACKGROUND ---
class StitchBackground:
    def __init__(self, master, image_name, opacity=0.7):
        try:
            sw, sh = master.winfo_screenwidth(), master.winfo_screenheight()
            img = Image.open(ASSETS_PATH / image_name).resize((sw, sh), Image.LANCZOS).convert("RGBA")
            alpha = img.split()[3]; alpha = ImageEnhance.Brightness(alpha).enhance(opacity); img.putalpha(alpha)
            base = Image.new("RGBA", img.size, COLOR_BG_OUT)
            self.render = ImageTk.PhotoImage(Image.alpha_composite(base, img))
            lbl = tk.Label(master, image=self.render, bg=COLOR_BG_OUT); lbl.place(x=0, y=0, relwidth=1, relheight=1)
            lbl.image = self.render; lbl.lower()
        except: pass

# --- FUNCTIONS ---
def handle_back():
    global current_step
    if current_step == 2:
        window.destroy()
        subprocess.Popen([sys.executable, 'camera_config_new.py'])
    else:
        window.destroy()
        subprocess.Popen([sys.executable, 'main_menu_new.py'])

def proceed_to_form():
    global current_step
    try:
        n = int(num_var.get())
        if 1 <= n <= 6:
            step1_frame.pack_forget()
            current_step = 2
            build_form(n)
        else: messagebox.showerror("Error", "Jumlah line harus 1-6.")
    except: messagebox.showerror("Error", "Masukkan angka valid.")

def build_form(n):
    global rows_data
    rows_data = []
    # Frame penampung di dalam main_card
    form_f = tk.Frame(main_card, bg=COLOR_CARD); form_f.pack(pady=5, fill="both", expand=True)
    
    try:
        with open(CONFIG_FILE, "r") as f: full_data = json.load(f)
    except: full_data = {"database": {}, "active_config": {}}
    
    db_keys = list(full_data.get("database", {}).keys())
    db_opts = db_keys + ["New Device (Manual)"]
    
    tk.Label(form_f, text="KONFIGURASI LINE PRODUKSI", font=("Segoe UI", 16, "bold"), bg=COLOR_CARD, fg=COLOR_PRIMARY).pack(pady=(20, 10))
    wrapper = tk.Frame(form_f, bg=COLOR_CARD); wrapper.pack(anchor="center")

    for i in range(n):
        line = f"Line {chr(65+i)}"
        row = tk.Frame(wrapper, bg=COLOR_CARD, pady=4); row.pack(fill="x")
        
        # Badge Line (A, B, C...)
        badge = tk.Frame(row, bg=COLOR_ACCENT, padx=8, pady=3); badge.pack(side="left", padx=(0, 10))
        tk.Label(badge, text=line, font=("Segoe UI", 8, "bold"), bg=COLOR_ACCENT, fg=COLOR_PRIMARY).pack()
        
        # Dropdown
        cv = tk.StringVar()
        combo = ttk.Combobox(row, textvariable=cv, values=db_opts, state="readonly", width=22)
        combo.pack(side="left", ipady=3)
        
        # Container Input Manual
        mc = tk.Frame(row, bg=COLOR_CARD)
        box_s = {"bg": "#F8FAFC", "highlightthickness": 1, "highlightbackground": "#CBD5E1", "padx": 5, "pady": 2}
        flds = []
        for k, w in [("IP:", 12), ("User:", 8), ("Pass:", 8)]:
            b = tk.Frame(mc, **box_s); b.pack(side="left", padx=5)
            tk.Label(b, text=k, bg="#F8FAFC", font=("Segoe UI", 7, "bold"), fg=TXT_SEC).pack(side="left")
            e = tk.Entry(b, width=w, font=("Segoe UI", 9), relief="flat", bg="#F8FAFC")
            if k == "Pass:": e.config(show="*")
            e.pack(side="left", padx=2); flds.append(e)

        # LOGIKA DROPDOWN: Hanya muncul manual jika pilih "New Device (Manual)"
        def toggle(event, mc=mc, cv=cv):
            if cv.get() == "New Device (Manual)":
                mc.pack(side="left")
            else:
                mc.pack_forget()

        combo.bind("<<ComboboxSelected>>", toggle)
        
        # Inisialisasi: Pilih data pertama dari JSON jika ada
        if db_keys:
            combo.current(0)
            mc.pack_forget()
        else:
            combo.set("New Device (Manual)")
            mc.pack(side="left")
            
        rows_data.append({"line": line, "combo": cv, "ip": flds[0], "user": flds[1], "pass": flds[2]})

    # TOMBOL SIMPAN (ROUNDED, BOLD, PUTIH)
    ctk.CTkButton(form_f, text="SIMPAN & AKTIFKAN MONITORING", 
                  command=lambda: submit_logic(full_data),
                  font=("Segoe UI", 12, "bold"), fg_color=COLOR_PRIMARY, 
                  text_color="white", width=380, height=52, corner_radius=6).pack(pady=30)

def submit_logic(data):
    addrs, names = [], []
    for itm in rows_data:
        if itm["combo"].get() == "New Device (Manual)":
            ip, user, pw = itm["ip"].get(), itm["user"].get(), itm["pass"].get()
            addrs.append(f"rtsp://{user}:{pw.replace('@','%40')}@{ip}:554{DEFAULT_RTSP}")
        else:
            addrs.append(data["database"].get(itm["combo"].get()))
        names.append(itm["line"])
    data["active_config"] = {"addresses": addrs, "names": names}
    with open(CONFIG_FILE, "w") as f: json.dump(data, f, indent=4)
    window.destroy()
    subprocess.Popen([sys.executable, 'main_coding_new.py'])

# --- WINDOW SETUP ---
window = tk.Tk()
window.attributes("-fullscreen", True)
window.configure(bg=COLOR_BG_OUT)
StitchBackground(window, "assets/bgpetro.jpeg", opacity=0.7)

# 1. TOMBOL POJOK (KOTAK & TK STANDAR)
tk.Button(window, text="Back", command=handle_back, font=("Segoe UI", 9, "bold"), 
          bg="#EF4444", fg="white", relief="flat", padx=15, pady=5, bd=0).place(relx=0.99, rely=0.01, anchor="ne")

tk.Button(window, text="Minimize", command=window.iconify, font=("Segoe UI", 9), 
          bg="#D1D5DB", relief="flat", padx=15, pady=5, bd=0).place(relx=0.94, rely=0.01, anchor="ne")

# 2. MAIN CARD (KOTAK & TK STANDAR)
main_card = tk.Frame(window, bg=COLOR_CARD, highlightthickness=0, bd=0)
main_card.place(relx=0.5, rely=0.5, anchor="center", width=900, height=600)

# Header Logo
h_f = tk.Frame(main_card, bg=COLOR_CARD); h_f.pack(pady=(40, 5))
try:
    for n, h in [("assets/danantara.png", 65), ("assets/pi.png", 65), ("assets/petro.png", 48)]:
        img = Image.open(ASSETS_PATH/n)
        ren = ImageTk.PhotoImage(img.resize((int(h*img.width/img.height), h), Image.LANCZOS))
        lbl = tk.Label(h_f, image=ren, bg=COLOR_CARD); lbl.image=ren; lbl.pack(side="left", padx=10)
except: pass

tk.Label(main_card, text="Smart Stitch Detection", font=("Segoe UI", 26, "bold"), bg=COLOR_CARD, fg=COLOR_PRIMARY).pack()
tk.Label(main_card, text="Konfigurasi Alamat Kamera CCTV", font=("Segoe UI", 10), bg=COLOR_CARD, fg=TXT_SEC).pack(pady=(0, 10))

# --- STEP 1 FRAME ---
step1_frame = tk.Frame(main_card, bg=COLOR_CARD); step1_frame.pack(expand=True, fill="both")
s1_in = tk.Frame(step1_frame, bg=COLOR_CARD); s1_in.place(relx=0.5, rely=0.4, anchor="center")
tk.Label(s1_in, text="Berapa banyak kamera yang akan dipantau?", font=("Segoe UI", 11, "bold"), bg=COLOR_CARD, fg=TXT_DARK).pack(pady=10)
num_var = tk.StringVar(value="4")
tk.Spinbox(s1_in, from_=1, to=6, textvariable=num_var, font=("Segoe UI", 20, "bold"), width=3, justify="center").pack(pady=10)

# TOMBOL LANJUTKAN (ROUNDED, BOLD, PUTIH)
ctk.CTkButton(s1_in, text="LANJUTKAN", command=proceed_to_form, 
              font=("Segoe UI", 13, "bold"), fg_color=COLOR_PRIMARY, 
              text_color="white", width=240, height=52, corner_radius=6).pack(pady=20)

tk.Label(main_card, text="Command Center | Departemen Pergudangan & Pengantongan", font=("Segoe UI", 8, "bold"), bg=COLOR_CARD, fg=TXT_DARK).pack(side="bottom", pady=25)

window.mainloop()