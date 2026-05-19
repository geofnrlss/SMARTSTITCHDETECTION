import os, sys, subprocess
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk 
from PIL import Image, ImageTk, ImageEnhance
from pathlib import Path

# --- KONFIGURASI STYLE ---
COLOR_PRIMARY  = "#183BC8" 
COLOR_BG_OUT   = "#EDF2F7" 
COLOR_CARD     = "#FFFFFF"
TXT_WHITE      = "#FFFFFF"
TXT_DARK       = "#1F2937"
TXT_SEC        = "#6B7280"
AUTHORIZED_PASSWORD = "admin"

ASSETS_PATH = Path(__file__).parent
ctk.set_appearance_mode("light")

# --- FUNCTIONS ---
def attempt_login(event=None):
    entered = password_entry.get()
    if entered == AUTHORIZED_PASSWORD:
        window.destroy()
        try:
            # Pastikan file main_menu_new.py ada di folder yang sama
            subprocess.run([sys.executable, 'main_menu_new.py'], check=True)
        except Exception as e:
            messagebox.showerror("Error", f"Sistem gagal dimuat: {e}")
    else:
        messagebox.showerror("Login Failed", "Password salah!")
        password_entry.delete(0, tk.END)

# --- WINDOW SETUP ---
window = tk.Tk()
window.title("Smart Stitch AI - Secure Login")
window.attributes("-fullscreen", True)
window.configure(bg=COLOR_BG_OUT) 

screen_width = window.winfo_screenwidth()
screen_height = window.winfo_screenheight()

# --- 1. BACKGROUND LAYAR UTAMA (70% Opacity) ---
try:
    bg_full = Image.open(ASSETS_PATH / "assets/bgpetro.jpeg").resize((screen_width, screen_height), Image.LANCZOS).convert("RGBA")
    alpha = bg_full.split()[3]
    alpha = ImageEnhance.Brightness(alpha).enhance(0.7) 
    bg_full.putalpha(alpha)
    render_full_bg = ImageTk.PhotoImage(Image.alpha_composite(Image.new("RGBA", bg_full.size, COLOR_BG_OUT), bg_full))
    tk.Label(window, image=render_full_bg, bg=COLOR_BG_OUT).place(x=0, y=0, relwidth=1, relheight=1)
except: pass

# --- 2. MAIN CARD LOGIN (KOTAK SIKU - 900x600) ---
# Sesuai permintaan, card utama tetap kotak (tk.Frame)
main_card = tk.Frame(window, bg=COLOR_CARD, highlightthickness=0, bd=0)
main_card.place(relx=0.5, rely=0.5, anchor="center", width=900, height=600)

# PANEL KIRI (Branding Area)
left_panel_width, left_panel_height = 400, 600
canvas_left = tk.Canvas(main_card, width=left_panel_width, height=left_panel_height, bg=COLOR_PRIMARY, highlightthickness=0, bd=0)
canvas_left.pack(side="left", fill="both")

try:
    img_p = Image.open(ASSETS_PATH / "assets/fotopabrik.jpeg").resize((left_panel_width, left_panel_height), Image.LANCZOS).convert("RGBA")
    alpha_p = img_p.split()[3]; alpha_p = ImageEnhance.Brightness(alpha_p).enhance(0.3); img_p.putalpha(alpha_p)
    render_l = ImageTk.PhotoImage(Image.alpha_composite(Image.new("RGBA", img_p.size, COLOR_PRIMARY), img_p))
    canvas_left.create_image(0, 0, anchor="nw", image=render_l); canvas_left.image = render_l 
    canvas_left.create_text(left_panel_width//2, 270, text="Smart Stitch\nDetection", font=("Segoe UI", 30, "bold"), fill=TXT_WHITE, justify="center")
    canvas_left.create_text(left_panel_width//2, 345, text="Sistem Monitoring Kualitas\nJahitan Karung Berbasis AI", font=("Segoe UI", 11), fill="#FFFFFF", justify="center")
except: pass

# PANEL KANAN (Form Area)
right_panel = tk.Frame(main_card, bg=COLOR_CARD, padx=60)
right_panel.pack(side="right", fill="both", expand=True)

# Logo-logo Atas
logo_frame = tk.Frame(right_panel, bg=COLOR_CARD); logo_frame.pack(pady=(50, 10)) 
try:
    for name, h in [("assets/danantara.png", 65), ("assets/pi.png", 65), ("assets/petro.png", 48)]:
        img = Image.open(ASSETS_PATH / name); ren = ImageTk.PhotoImage(img.resize((int(h * img.width / img.height), h), Image.LANCZOS))
        lbl = tk.Label(logo_frame, image=ren, bg=COLOR_CARD); lbl.image = ren; lbl.pack(side="left", padx=8)
except: pass

# Judul & Instruksi
tk.Label(right_panel, text="Login", font=("Segoe UI", 24, "bold"), bg=COLOR_CARD, fg=TXT_DARK).pack(pady=(5, 5))
tk.Label(right_panel, text="Masukkan password akses admin gudang", font=("Segoe UI", 10), bg=COLOR_CARD, fg=TXT_SEC).pack(pady=(0, 20))

# --- INPUT PASSWORD DENGAN IKON KUNCI ---
tk.Label(right_panel, text="PASSWORD", font=("Segoe UI", 8, "bold"), bg=COLOR_CARD, fg=TXT_SEC).pack(anchor="w", padx=2, pady=(10, 0))

# Container rounded untuk menyatukan ikon dan entry
pass_container = ctk.CTkFrame(right_panel, fg_color="#F8FAFC", border_color="#E2E8F0", border_width=1, corner_radius=10, height=45)
pass_container.pack(fill="x", pady=(5, 25))
pass_container.pack_propagate(False)

# Ikon Kunci di kiri
lock_icon = ctk.CTkLabel(pass_container, text="🔒", font=("Segoe UI", 13), text_color="#94A3B8")
lock_icon.pack(side="left", padx=(15, 0))

# Entry Password (Tanpa border sendiri karena ikut container)
password_entry = ctk.CTkEntry(
    pass_container, 
    show="*", 
    font=("Segoe UI", 12), 
    fg_color="transparent", 
    border_width=0, 
    text_color=TXT_DARK,
    placeholder_text="Password"
)
password_entry.pack(side="left", fill="both", expand=True, padx=(5, 10))
password_entry.focus_set()
password_entry.bind('<Return>', attempt_login)

# --- TOMBOL LOGIN (ROUNDED & BOLD PUTIH) ---
login_btn = ctk.CTkButton(
    right_panel, 
    text="LOGIN KE DASHBOARD", 
    font=("Segoe UI", 13, "bold"), 
    fg_color=COLOR_PRIMARY, 
    hover_color="#132da1", 
    text_color="white", 
    height=50, 
    corner_radius=12, 
    command=attempt_login
)
login_btn.pack(fill="x")

# Footer
tk.Label(right_panel, text="Departemen Pergudangan & Pengantongan", font=("Segoe UI", 8, "bold"), bg=COLOR_CARD, fg=TXT_DARK).pack(side="bottom", pady=25)

# --- TOMBOL EXIT (KOTAK SIKU) ---
tk.Button(window, text="✕", font=("Arial", 12), bg=COLOR_CARD, fg=TXT_SEC, relief="flat", command=window.destroy, cursor="hand2").place(relx=0.99, rely=0.01, anchor="ne")

window.mainloop()