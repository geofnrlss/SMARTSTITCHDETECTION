import os, sys, json, subprocess
import tkinter as tk
import customtkinter as ctk 
from tkinter import messagebox, filedialog
from PIL import Image, ImageTk, ImageEnhance
from pathlib import Path

# --- AUTO VENV CHECK ---
base_dir = os.path.dirname(os.path.abspath(__file__))
venv_py = os.path.join(base_dir, "venv", "Scripts", "python.exe")
if os.path.exists(venv_py) and os.path.normcase(sys.executable) != os.path.normcase(venv_py):
    os.execv(venv_py, [venv_py] + sys.argv)

# --- CONFIGURATION ---
COLOR_PRIMARY  = "#183BC8" 
COLOR_BG_OUT   = "#EDF2F7"
COLOR_CARD     = "#FFFFFF"
TXT_DARK       = "#1F2937"
TXT_SEC        = "#6B7280"
CONFIG_FILE    = "rtsp_config.json"
ASSETS_PATH    = Path(__file__).parent

ctk.set_appearance_mode("light") 

# --- CLASS BACKGROUND ---
class StitchBackground:
    def __init__(self, master, image_name, opacity=0.7):
        try:
            sw, sh = master.winfo_screenwidth(), master.winfo_screenheight()
            img = Image.open(ASSETS_PATH / image_name).resize((sw, sh), Image.LANCZOS).convert("RGBA")
            alpha = img.split()[3]
            alpha = ImageEnhance.Brightness(alpha).enhance(opacity)
            img.putalpha(alpha)
            base = Image.new("RGBA", img.size, COLOR_BG_OUT)
            self.render = ImageTk.PhotoImage(Image.alpha_composite(base, img))
            lbl = tk.Label(master, image=self.render, bg=COLOR_BG_OUT)
            lbl.place(x=0, y=0, relwidth=1, relheight=1)
            lbl.image = self.render
            lbl.lower()
        except: pass

# --- FUNCTIONS ---
def handle_logout():
    if messagebox.askyesno("Logout", "Yakin ingin keluar?"):
        window.destroy()
        subprocess.Popen([sys.executable, 'login_new.pyw'])

def open_camera_config():
    window.destroy()
    subprocess.Popen([sys.executable, 'camera_config_new.py'])

def select_video_file():
    f_path = filedialog.askopenfilename(title="Pilih File Video", filetypes=[("Video Files", "*.mp4 *.avi *.mov *.mkv")])
    if f_path:
        try:
            with open(CONFIG_FILE, "w") as f: json.dump({"file": f_path}, f)
            window.destroy()
            subprocess.Popen([sys.executable, 'selectfile_terbarufinal.py'])
        except: pass

# --- WINDOW SETUP ---
window = tk.Tk()
window.attributes("-fullscreen", True)
window.configure(bg=COLOR_BG_OUT)

# 1. APPLY BACKGROUND (Wajib Muncul)
StitchBackground(window, "assets/bgpetro.jpeg", opacity=0.7)

# 2. TOP BUTTONS (Minimize & Logout) - Tetap Pakai TK Biasa Biar Rapet
btn_logout = tk.Button(window, text="Logout", command=handle_logout, font=("Segoe UI", 9, "bold"), 
                       bg="#EF4444", fg="white", relief="flat", padx=12, pady=5, bd=0)
btn_logout.place(relx=0.99, rely=0.01, anchor="ne")

btn_min = tk.Button(window, text="Minimize", command=window.iconify, font=("Segoe UI", 9), 
                    bg="#D1D5DB", relief="flat", padx=12, pady=5, bd=0)
btn_min.place(relx=0.94, rely=0.01, anchor="ne")

# 3. MAIN CARD
main_card = tk.Frame(window, bg=COLOR_CARD, highlightthickness=0, bd=0)
main_card.place(relx=0.5, rely=0.5, anchor="center", width=900, height=600)

# Header Logo
h_f = tk.Frame(main_card, bg=COLOR_CARD); h_f.pack(pady=(40, 5))
try:
    for n, h in [("assets/danantara.png", 65), ("assets/pi.png", 65), ("assets/petro.png", 48)]:
        img = Image.open(ASSETS_PATH/n)
        ren = ImageTk.PhotoImage(img.resize((int(h*img.width/img.height), h), Image.LANCZOS))
        lbl = tk.Label(h_f, image=ren, bg=COLOR_CARD); lbl.image=ren; lbl.pack(side="left", padx=12)
except: pass

tk.Label(main_card, text="Smart Stitch Detection", font=("Segoe UI", 26, "bold"), bg=COLOR_CARD, fg=COLOR_PRIMARY).pack()
tk.Label(main_card, text="Sistem Monitoring Kualitas Jahitan Karung Berbasis AI", font=("Segoe UI", 10), bg=COLOR_CARD, fg=TXT_SEC).pack(pady=(0, 20))

# --- BUTTON AREA (FIXED STYLE) ---
menu_f = tk.Frame(main_card, bg=COLOR_CARD); menu_f.pack(expand=True)

# Font Khusus CTK (Dibuat agak besar biar Bold-nya berasa)
button_font = ("Segoe UI", 13, "bold")

# Tombol Live
btn_live = ctk.CTkButton(menu_f, 
                         text="CAMERA MONITORING (LIVE)", 
                         command=open_camera_config,
                         fg_color=COLOR_PRIMARY, 
                         hover_color="#132da1",
                         text_color="white",          # <--- Paksa warna putih
                         font=button_font,            # <--- Pakai font bold 13
                         width=320, 
                         height=55,                   # <--- Sedikit lebih tebal
                         corner_radius=6)            # <--- Rounded manis
btn_live.pack(pady=10)

# Tombol Offline
btn_off = ctk.CTkButton(menu_f, 
                        text="SELECT VIDEO FILE (OFFLINE)", 
                        command=select_video_file,
                        fg_color="#10B981", 
                        hover_color="#0d9469",
                        text_color="white",           # <--- Paksa warna putih
                        font=button_font,             # <--- Pakai font bold 13
                        width=320, 
                        height=55,                    # <--- Sedikit lebih tebal
                        corner_radius=6)             # <--- Rounded manis
btn_off.pack(pady=10)

tk.Label(main_card, text="Command Center | Departemen Pergudangan & Pengantongan", font=("Segoe UI", 8, "bold"), bg=COLOR_CARD, fg=TXT_DARK).pack(side="bottom", pady=25)

window.mainloop()