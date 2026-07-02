"""
gui/login_window.py — PayrollPro v3.0
Cleaner, real-company login. DPI-aware for sharp rendering.
"""
import tkinter as tk
from tkinter import messagebox, ttk
import sys


# ============================================================================
#  PALETTE  ::  Pine & Pearl (M1-C)
# ============================================================================
PALETTE = {
    "sidebar":         "#1F3D33",
    "sidebar_alt":     "#2F5447",
    "bg":              "#F2F3F1",
    "card":            "#FFFFFF",
    "card_border":     "#D9DCD7",
    "text":            "#2A332E",
    "text_secondary":  "#4D5651",
    "text_muted":      "#7A857F",
    "text_on_sidebar": "#F4F4F2",
    "text_on_sidebar_muted": "#A8B0AB",
    "accent":          "#C0C4BD",
    "accent_dark":     "#9DAEA6",
    "deduction":       "#9A6332",
    "earning":         "#2F5447",
    "net_card":        "#1F3D33",
    "field_bg":        "#F7F8F6",
}


def enable_dpi_awareness():
    """
    Tell Windows this app handles its own DPI scaling.
    Without this, Windows stretches a low-res bitmap -> blurry text.
    Safe no-op on non-Windows systems.
    """
    if sys.platform == "win32":
        try:
            from ctypes import windll
            try:
                windll.shcore.SetProcessDpiAwareness(2)   # per-monitor aware
            except Exception:
                windll.user32.SetProcessDPIAware()         # system aware (older Windows)
        except Exception:
            pass


def tune_scaling(win):
    """Match Tk's internal scaling to the screen DPI for crisp text."""
    try:
        dpi = win.winfo_fpixels("1i")
        win.tk.call("tk", "scaling", dpi / 72.0)
    except Exception:
        pass


def show_login(on_success):
    enable_dpi_awareness()

    win = tk.Tk()
    win.title("PayrollPro")
    win.geometry("440x540")
    win.configure(bg=PALETTE["bg"])
    win.resizable(False, False)
    tune_scaling(win)

    base_font = "Segoe UI"

    style = ttk.Style()
    try:
        style.theme_use("clam")
    except Exception:
        pass
    style.configure("Login.TEntry",
                    fieldbackground=PALETTE["field_bg"],
                    foreground=PALETTE["text"],
                    bordercolor=PALETTE["card_border"],
                    lightcolor=PALETTE["card_border"],
                    darkcolor=PALETTE["card_border"],
                    insertcolor=PALETTE["sidebar"],
                    padding=10, relief="flat")
    style.map("Login.TEntry", bordercolor=[("focus", PALETTE["sidebar_alt"])])

    outer = tk.Frame(win, bg=PALETTE["bg"])
    outer.pack(fill="both", expand=True)

    card = tk.Frame(outer, bg=PALETTE["card"],
                    highlightbackground=PALETTE["card_border"],
                    highlightthickness=1)
    card.place(relx=0.5, rely=0.5, anchor="center", width=360, height=440)

    logo_wrap = tk.Frame(card, bg=PALETTE["card"])
    logo_wrap.pack(pady=(34, 6))
    tk.Label(logo_wrap, text="Rs", bg=PALETTE["sidebar"],
             fg=PALETTE["accent"], font=(base_font, 16, "bold"),
             width=3, height=1, padx=2, pady=4).pack()

    tk.Label(card, text="PayrollPro",
             bg=PALETTE["card"], fg=PALETTE["text"],
             font=(base_font, 18, "bold")).pack(pady=(8, 0))
    tk.Label(card, text="Sign in to continue",
             bg=PALETTE["card"], fg=PALETTE["text_muted"],
             font=(base_font, 10)).pack(pady=(2, 0))

    tk.Label(card, text="Username",
             bg=PALETTE["card"], fg=PALETTE["text_secondary"],
             font=(base_font, 9, "bold")).pack(anchor="w", padx=36, pady=(26, 4))
    user_entry = ttk.Entry(card, font=(base_font, 11), style="Login.TEntry")
    user_entry.pack(padx=36, fill="x")
    user_entry.insert(0, "admin")

    tk.Label(card, text="Password",
             bg=PALETTE["card"], fg=PALETTE["text_secondary"],
             font=(base_font, 9, "bold")).pack(anchor="w", padx=36, pady=(16, 4))
    pwd_entry = ttk.Entry(card, font=(base_font, 11), style="Login.TEntry", show="•")
    pwd_entry.pack(padx=36, fill="x")

    def attempt_login(_event=None):
        u = user_entry.get().strip()
        p = pwd_entry.get().strip()
        if u == "admin" and p == "admin123":
            win.destroy()
            on_success()
        else:
            messagebox.showerror("Sign in failed",
                                 "Invalid credentials.\nUse  admin  /  admin123")
            pwd_entry.delete(0, "end")
            pwd_entry.focus()

    btn = tk.Button(card, text="Sign in", command=attempt_login,
                    bg=PALETTE["sidebar"], fg=PALETTE["text_on_sidebar"],
                    activebackground=PALETTE["sidebar_alt"],
                    activeforeground="white",
                    relief="flat", borderwidth=0,
                    font=(base_font, 11, "bold"), cursor="hand2")
    btn.pack(padx=36, pady=(26, 0), fill="x", ipady=9)
    btn.bind("<Enter>", lambda e: btn.configure(bg=PALETTE["sidebar_alt"]))
    btn.bind("<Leave>", lambda e: btn.configure(bg=PALETTE["sidebar"]))

    win.bind("<Return>", attempt_login)
    pwd_entry.focus()

    tk.Label(win, text="admin  /  admin123",
             bg=PALETTE["bg"], fg=PALETTE["text_muted"],
             font=(base_font, 8)).pack(side="bottom", pady=12)

    win.mainloop()
