"""
================================================================================
  SENTINEL OS :: FOCUS SHADE MATRIX (FIXED BUILD)
  File Name: sentinel_focus_shade.pyw
  Stack: Python 3.10+ | Tkinter Matrix | WinAPI Mutex | pynput | pystray | Pillow
================================================================================
"""

import os
import sys
import io
import time
import ctypes
from ctypes import wintypes
import threading
import subprocess
import winreg
from pathlib import Path
import tkinter as tk
from tkinter import messagebox

# 1. Защита от дубликатов процессов через системный мьютекс Windows
MUTEX_NAME = "Global\\SentinelFocusShadeMatrix_Mutex_V7"
kernel32 = ctypes.windll.kernel32
user32 = ctypes.windll.user32

mutex = kernel32.CreateMutexW(None, False, MUTEX_NAME)
last_error = kernel32.GetLastError()
ERROR_ALREADY_EXISTS = 183

if last_error == ERROR_ALREADY_EXISTS:
    sys.exit(0)

# Изоляция потоков для pythonw
if sys.stdout is None:
    sys.stdout = io.StringIO()
if sys.stderr is None:
    sys.stderr = io.StringIO()

# Автоустановка библиотек при старте
REQUIRED_PACKAGES = {
    "PIL": "Pillow",
    "pystray": "pystray",
    "pynput": "pynput"
}

def ensure_dependencies():
    missing = []
    for mod_name, pkg_name in REQUIRED_PACKAGES.items():
        try:
            __import__(mod_name)
        except ImportError:
            missing.append(pkg_name)
    if missing:
        creationflags = 0x08000000 if sys.platform == "win32" else 0
        for pkg in missing:
            try:
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", pkg, "--quiet"],
                    creationflags=creationflags
                )
            except Exception:
                pass

ensure_dependencies()

from PIL import Image, ImageDraw
import pystray
from pynput import keyboard, mouse

# WinAPI ID приложения
try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("sentinel.focus.shade.matrix.v7")
except Exception:
    pass

GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOOLWINDOW = 0x00000080

# Цветовая палитра Sentinel Deck
BG_DARK = "#050a12"
BG_PANEL = "#0a1322"
BG_CARD = "#0f1c30"
BG_ACTIVE = "#16335a"
BORDER_CLR = "#1e293b"
BORDER_NEON = "#38bdf8"

COLOR_CYAN = "#38bdf8"
COLOR_GREEN = "#10b981"
COLOR_RED = "#f43f5e"
COLOR_AMBER = "#f59e0b"
COLOR_BLUE = "#0284c7"
TEXT_WHITE = "#f8fafc"
TEXT_MUTED = "#64748b"
TERMINAL_GREEN = "#22c55e"

FONT_CONSOLE = ("Consolas", 9)
FONT_CONSOLE_BOLD = ("Consolas", 9, "bold")
FONT_TITLE = ("Consolas", 11, "bold")
FONT_STATUS = ("Consolas", 10, "bold")
FONT_MON_NAME = ("Consolas", 13, "bold")


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


class MONITORINFOEX(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", RECT),
        ("rcWork", RECT),
        ("dwFlags", wintypes.DWORD),
        ("szDevice", wintypes.WCHAR * 32),
    ]


class DISPLAY_DEVICE(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("DeviceName", wintypes.WCHAR * 32),
        ("DeviceString", wintypes.WCHAR * 128),
        ("StateFlags", wintypes.DWORD),
        ("DeviceID", wintypes.WCHAR * 128),
        ("DeviceKey", wintypes.WCHAR * 128),
    ]


def get_all_monitors():
    monitors = []

    def monitor_enum_proc(hMonitor, hdcMonitor, lprcMonitor, dwData):
        mi = MONITORINFOEX()
        mi.cbSize = ctypes.sizeof(MONITORINFOEX)
        if user32.GetMonitorInfoW(hMonitor, ctypes.byref(mi)):
            rc = mi.rcMonitor
            is_hardware_primary = bool(mi.dwFlags & 1)
            adapter_name = mi.szDevice

            friendly_name = f"Display-{len(monitors) + 1}"
            dd_mon = DISPLAY_DEVICE()
            dd_mon.cb = ctypes.sizeof(DISPLAY_DEVICE)
            if user32.EnumDisplayDevicesW(adapter_name, 0, ctypes.byref(dd_mon), 0):
                n = dd_mon.DeviceString.strip()
                if n and "generic" not in n.lower() and "универсальный" not in n.lower():
                    friendly_name = n

            monitors.append({
                "device": adapter_name,
                "friendly_name": friendly_name,
                "x": rc.left,
                "y": rc.top,
                "w": rc.right - rc.left,
                "h": rc.bottom - rc.top,
                "is_hw_primary": is_hardware_primary
            })
        return True

    ENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HMONITOR, wintypes.HDC, ctypes.POINTER(RECT), wintypes.LPARAM)
    user32.EnumDisplayMonitors(None, None, ENUMPROC(monitor_enum_proc), 0)
    return monitors


def make_window_click_through(hwnd: int):
    try:
        style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        style |= WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
    except Exception:
        pass


def create_circular_icon():
    img = Image.new("RGBA", (64, 64), color=(0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse((2, 2, 62, 62), fill="#0a1322", outline="#10b981", width=3)
    draw.ellipse((10, 10, 54, 54), fill="#050a12", outline="#38bdf8", width=2)
    draw.ellipse((24, 24, 40, 40), fill="#10b981")
    return img


# ------------------------------------------------------------------------------
# ПОСТОЯННЫЙ ОВЕРЛЕЙ ЗАТЕМНЕНИЯ
# ------------------------------------------------------------------------------
class PersistentDimmer(tk.Toplevel):
    def __init__(self, master, mon):
        super().__init__(master)
        self.mon = mon

        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(bg="#000000")

        self.geometry(f"{mon['w']}x{mon['h']}+{mon['x']}+{mon['y']}")
        self.attributes("-alpha", 0.0)

        self.update_idletasks()
        try:
            hwnd = user32.GetParent(self.winfo_id()) or self.winfo_id()
            make_window_click_through(hwnd)
        except Exception:
            pass

    def apply_shade(self, state: bool, alpha: float):
        self.attributes("-alpha", alpha if state else 0.0)


# ------------------------------------------------------------------------------
# ГЛАВНОЕ ОКНО CYBER DECK
# ------------------------------------------------------------------------------
class SentinelDimmerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Sentinel OS :: Focus Shade Matrix")
        self.geometry("880x620")
        self.minsize(760, 520)
        self.configure(bg=BG_DARK)

        self._apply_custom_app_icon()

        self.monitors = []
        self.persistent_overlays = []
        self.rendered_map_rects = []
        self.selected_primary_idx = 0
        self.current_mouse_mon_idx = 0

        # По умолчанию СТРОГО ВЫКЛЮЧЕНО
        self.dimmer_active = tk.BooleanVar(value=False)
        self.follow_mouse_strict = tk.BooleanVar(value=True)  # Чекбокс режима следования за мышью
        self.shade_level = tk.DoubleVar(value=0.80)
        self.autostart_var = tk.BooleanVar(value=self._check_autostart())

        # Бинды клавиш
        self.current_combo = "F9"
        self.combo_label_var = tk.StringVar(value="⌨ БИНД: F9")
        self.is_listening_combo = False
        self.currently_pressed = set()
        self.collected_combo = set()

        self._setup_ui()
        self._refresh_monitors()
        self._start_input_engine()

        # Показываем окно сразу
        self.deiconify()
        self.lift()
        self.attributes("-topmost", True)
        self.after(200, lambda: self.attributes("-topmost", False))
        self.focus_force()

        # Анимация и опрос мыши
        self.pulse_phase = 0.0
        self._animate_status_pulse()

        self.mouse_worker_running = True
        self.thread_mouse = threading.Thread(target=self._mouse_tracker, daemon=True)
        self.thread_mouse.start()

        # Системный трей
        self.tray_icon = None
        self._setup_tray()

        self.protocol("WM_DELETE_WINDOW", self.hide_to_tray)

    def _apply_custom_app_icon(self):
        try:
            self.icon_image = create_circular_icon()
            temp_ico = Path(os.environ.get("TEMP", ".")) / "sentinel_focus_fixed_ico.ico"
            self.icon_image.save(temp_ico, format="ICO")
            self.iconbitmap(str(temp_ico))
        except Exception:
            pass

    def _setup_ui(self):
        # 1. Верхний статус-бар
        status_bar = tk.Frame(self, bg=BG_DARK, height=36)
        status_bar.pack(fill=tk.X, padx=14, pady=(10, 4))

        self.status_dot = tk.Canvas(status_bar, width=14, height=14, bg=BG_DARK, highlightthickness=0)
        self.status_dot.pack(side=tk.LEFT, padx=(2, 8))

        self.lbl_status = tk.Label(
            status_bar, text="SENTINEL DECK ACTIVE", font=FONT_STATUS,
            bg=BG_DARK, fg=COLOR_GREEN
        )
        self.lbl_status.pack(side=tk.LEFT)

        self.lbl_dim_info = tk.Label(
            status_bar, text="[ ФОКУС: ВЫКЛ ]", font=FONT_CONSOLE_BOLD,
            bg=BG_DARK, fg=TEXT_MUTED
        )
        self.lbl_dim_info.pack(side=tk.LEFT, padx=16)

        self.btn_autostart = tk.Button(
            status_bar,
            text=f"🚀 АВТОЗАПУСК: [{'ВКЛ' if self.autostart_var.get() else 'ВЫКЛ'}]",
            font=FONT_CONSOLE_BOLD, bg=BG_CARD, fg=COLOR_GREEN if self.autostart_var.get() else TEXT_MUTED,
            bd=1, relief="solid", highlightbackground=BORDER_CLR, padx=10, pady=3,
            command=self._toggle_autostart
        )
        self.btn_autostart.pack(side=tk.RIGHT)

        # 2. Ряд функциональных кнопок
        actions_bar = tk.Frame(self, bg=BG_DARK)
        actions_bar.pack(fill=tk.X, padx=14, pady=4)

        self.btn_toggle = self._create_btn(
            actions_bar, "⚡ Включить Фокус", COLOR_BLUE, TEXT_WHITE, self.toggle_dimmer
        )
        self.btn_toggle.pack(side=tk.LEFT, padx=(0, 8))

        btn_rescan = self._create_btn(
            actions_bar, "⟳ Обновить сетку", BG_CARD, TEXT_WHITE, self._refresh_monitors
        )
        btn_rescan.pack(side=tk.LEFT, padx=4)

        self.btn_bind = tk.Button(
            actions_bar, textvariable=self.combo_label_var, font=FONT_CONSOLE_BOLD,
            bg=COLOR_AMBER, fg="#000000", bd=0, padx=14, pady=7,
            activebackground="#b45309", activeforeground=TEXT_WHITE,
            command=self._start_listening_combo
        )
        self.btn_bind.pack(side=tk.LEFT, padx=6)

        btn_tray = self._create_btn(
            actions_bar, "📥 В трей", COLOR_GREEN, "#000000", self.hide_to_tray
        )
        btn_tray.pack(side=tk.RIGHT)

        # 3. Интерактивная карта мониторов
        map_wrapper = tk.Frame(self, bg=BG_PANEL, bd=1, relief="solid", highlightbackground=BORDER_CLR)
        map_wrapper.pack(fill=tk.BOTH, expand=True, padx=14, pady=6)

        map_head = tk.Frame(map_wrapper, bg=BG_PANEL)
        map_head.pack(fill=tk.X, padx=12, pady=(8, 4))
        tk.Label(map_head, text="СЕТКА ДИСПЛЕЕВ WINDOWS", font=FONT_TITLE, bg=BG_PANEL, fg=COLOR_CYAN).pack(side=tk.LEFT)
        tk.Label(map_head, text="[ КЛИК ЛКМ ПО МОНИТОРУ = СДЕЛАТЬ ОСНОВНЫМ ]", font=FONT_CONSOLE_BOLD, bg=BG_PANEL, fg=COLOR_GREEN).pack(side=tk.RIGHT)

        self.canvas_map = tk.Canvas(map_wrapper, bg=BG_DARK, highlightthickness=0)
        self.canvas_map.pack(fill=tk.BOTH, expand=True, padx=8, pady=(4, 8))
        self.canvas_map.bind("<Configure>", lambda e: self._draw_monitor_layout())
        self.canvas_map.bind("<Button-1>", self._on_canvas_click)

        # 4. Панель параметров
        opt_bar = tk.Frame(self, bg=BG_PANEL, bd=1, relief="solid", highlightbackground=BORDER_CLR)
        opt_bar.pack(fill=tk.X, padx=14, pady=4)

        tk.Label(opt_bar, text="ЗАТЕМНЕНИЕ:", font=FONT_CONSOLE_BOLD, bg=BG_PANEL, fg=TEXT_WHITE).pack(side=tk.LEFT, padx=(12, 4), pady=8)
        self.lbl_slider_val = tk.Label(opt_bar, text="80%", font=FONT_CONSOLE_BOLD, bg=BG_PANEL, fg=COLOR_CYAN)
        self.lbl_slider_val.pack(side=tk.LEFT, padx=(0, 8))

        self.slider = tk.Scale(
            opt_bar, from_=0.20, to=1.00, resolution=0.05,
            orient=tk.HORIZONTAL, variable=self.shade_level, showvalue=False,
            bg=BG_PANEL, fg=COLOR_CYAN, highlightthickness=0,
            troughcolor=BG_DARK, activebackground=COLOR_GREEN, length=180,
            command=self._on_slider_change
        )
        self.slider.pack(side=tk.LEFT, padx=6)

        # Переключатель: следовать за мышью или держать основной
        chk_follow = tk.Checkbutton(
            opt_bar, text="Следовать за мышью (все темные, кроме монитора с курсором)",
            variable=self.follow_mouse_strict, font=FONT_CONSOLE_BOLD,
            bg=BG_PANEL, fg=COLOR_CYAN, selectcolor=BG_DARK,
            activebackground=BG_PANEL, activeforeground=COLOR_GREEN,
            command=self._on_follow_mode_toggle
        )
        chk_follow.pack(side=tk.RIGHT, padx=12)

        # 5. Компактный терминал
        term_wrapper = tk.Frame(self, bg=BG_DARK, height=85, bd=1, relief="solid", highlightbackground=BORDER_CLR)
        term_wrapper.pack(fill=tk.X, padx=14, pady=(4, 10))
        term_wrapper.pack_propagate(False)

        self.txt_terminal = tk.Text(
            term_wrapper, bg=BG_DARK, fg=TERMINAL_GREEN, font=FONT_CONSOLE,
            bd=0, padx=8, pady=4, wrap=tk.WORD, height=3
        )
        self.txt_terminal.pack(fill=tk.BOTH, expand=True)

        cmd_line = tk.Frame(term_wrapper, bg=BG_DARK)
        cmd_line.pack(side=tk.BOTTOM, fill=tk.X, padx=8, pady=(0, 2))
        tk.Label(cmd_line, text="Sentinel:~$", font=FONT_CONSOLE_BOLD, bg=BG_DARK, fg=COLOR_GREEN).pack(side=tk.LEFT)
        self.lbl_cmd_hint = tk.Label(cmd_line, text=f" готов к работе. Бинд: {self.current_combo}", font=FONT_CONSOLE, bg=BG_DARK, fg=TEXT_MUTED)
        self.lbl_cmd_hint.pack(side=tk.LEFT, padx=6)

    def _create_btn(self, parent, text, bg, fg, cmd):
        btn = tk.Button(
            parent, text=text, font=FONT_CONSOLE_BOLD,
            bg=bg, fg=fg, bd=0, padx=14, pady=7,
            activebackground="#1e3a5f", activeforeground=TEXT_WHITE,
            command=cmd
        )
        btn.bind("<Enter>", lambda e: btn.config(bg="#1e3a5f"))
        btn.bind("<Leave>", lambda e: btn.config(bg=bg))
        return btn

    def log(self, text: str):
        t_str = time.strftime("[%H:%M:%S]")
        self.txt_terminal.insert(tk.END, f"{t_str} {text}\n")
        self.txt_terminal.see(tk.END)

    def _animate_status_pulse(self):
        self.pulse_phase += 0.15
        color = COLOR_CYAN if self.dimmer_active.get() else COLOR_GREEN
        self.status_dot.delete("all")
        self.status_dot.create_oval(2, 2, 12, 12, fill=color, outline=BORDER_NEON if self.dimmer_active.get() else "#059669", width=2)
        self.after(60, self._animate_status_pulse)

    def _on_slider_change(self, val):
        self.lbl_slider_val.config(text=f"{int(float(val) * 100)}%")
        self._update_overlay_states()

    def _on_follow_mode_toggle(self):
        if self.follow_mouse_strict.get():
            self.log("Режим: активен только монитор под курсором (Strict Follow).")
        else:
            self.log(f"Режим: фиксированный основной экран #{self.selected_primary_idx + 1}, остальные темные.")
        self._update_overlay_states()

    # --------------------------------------------------------------------------
    # ОТРИСОВКА КАРТЫ С ВОЗМОЖНОСТЬЮ ВЫБОРА ОСНОВНОГО ЭКРАНА
    # --------------------------------------------------------------------------
    def _draw_monitor_layout(self):
        self.canvas_map.delete("all")
        self.rendered_map_rects = []

        if not self.monitors:
            return

        c_w = self.canvas_map.winfo_width()
        c_h = self.canvas_map.winfo_height()
        if c_w < 50 or c_h < 50:
            return

        # Фоновая кибер-сетка
        for x in range(0, c_w, 40):
            self.canvas_map.create_line(x, 0, x, c_h, fill="#0a121e", width=1)
        for y in range(0, c_h, 40):
            self.canvas_map.create_line(0, y, c_w, y, fill="#0a121e", width=1)

        min_x = min(m["x"] for m in self.monitors)
        max_x = max(m["x"] + m["w"] for m in self.monitors)
        min_y = min(m["y"] for m in self.monitors)
        max_y = max(m["y"] + m["h"] for m in self.monitors)

        total_w = max_x - min_x
        total_h = max_y - min_y
        if total_w <= 0 or total_h <= 0:
            return

        pad = 30
        scale = min((c_w - pad * 2) / total_w, (c_h - pad * 2) / total_h)
        base_off_x = (c_w - (total_w * scale)) / 2
        base_off_y = (c_h - (total_h * scale)) / 2

        for idx, m in enumerate(self.monitors):
            rx1 = base_off_x + (m["x"] - min_x) * scale
            ry1 = base_off_y + (m["y"] - min_y) * scale
            rx2 = rx1 + m["w"] * scale
            ry2 = ry1 + m["h"] * scale

            is_primary = (idx == self.selected_primary_idx)
            is_mouse_here = (idx == self.current_mouse_mon_idx)

            fill_clr = BG_ACTIVE if is_primary else BG_CARD
            border_clr = COLOR_GREEN if is_mouse_here else (COLOR_BLUE if is_primary else BORDER_CLR)
            border_w = 3 if is_primary else (2 if is_mouse_here else 1)

            rect_id = self.canvas_map.create_rectangle(
                rx1, ry1, rx2, ry2,
                fill=fill_clr, outline=border_clr, width=border_w
            )

            # Номер монитора
            self.canvas_map.create_text(
                (rx1 + rx2) / 2, (ry1 + ry2) / 2 - 10,
                text=str(idx + 1), font=FONT_MON_NAME, fill=TEXT_WHITE
            )

            tag = "[ ОСНОВНОЙ ]" if is_primary else "[ SHADE ]"
            if is_mouse_here and self.follow_mouse_strict.get():
                tag = "● [ КУРСОР ]"

            tag_color = COLOR_GREEN if is_mouse_here else (COLOR_CYAN if is_primary else TEXT_MUTED)
            self.canvas_map.create_text(
                (rx1 + rx2) / 2, (ry1 + ry2) / 2 + 12,
                text=tag, font=FONT_CONSOLE_BOLD, fill=tag_color
            )

            self.rendered_map_rects.append({
                "idx": idx,
                "rect": (rx1, ry1, rx2, ry2),
                "mon": m
            })

    def _on_canvas_click(self, event):
        cx, cy = event.x, event.y
        for item in self.rendered_map_rects:
            x1, y1, x2, y2 = item["rect"]
            if x1 <= cx <= x2 and y1 <= cy <= y2:
                idx = item["idx"]
                if self.selected_primary_idx != idx:
                    self.selected_primary_idx = idx
                    self.log(f"Назначен основной монитор: #{idx + 1} ({item['mon']['friendly_name']})")
                    self._draw_monitor_layout()
                    self._update_overlay_states()
                break

    # --------------------------------------------------------------------------
    # УПРАВЛЕНИЕ ЗАТЕМНЕНИЕМ (БЕЗ МЕРЦАНИЯ)
    # --------------------------------------------------------------------------
    def _refresh_monitors(self):
        for ov in self.persistent_overlays:
            try:
                ov.destroy()
            except Exception:
                pass
        self.persistent_overlays.clear()

        self.monitors = get_all_monitors()

        # Первично выставляем аппаратный primary
        for idx, m in enumerate(self.monitors):
            if m["is_hw_primary"]:
                self.selected_primary_idx = idx
                break

        for m in self.monitors:
            self.persistent_overlays.append(PersistentDimmer(self, m))

        self.log(f"Сетка обновлена: обнаружено {len(self.monitors)} монитора(ов).")
        self.after(50, self._draw_monitor_layout)
        self._update_overlay_states()

    def _update_overlay_states(self):
        lvl = self.shade_level.get()
        active = self.dimmer_active.get()

        for idx, ov in enumerate(self.persistent_overlays):
            if not active:
                ov.apply_shade(False, 0.0)
            else:
                if self.follow_mouse_strict.get():
                    # Режим следования: чистый ТОЛЬКО монитор с мышью
                    should_shade = (idx != self.current_mouse_mon_idx)
                else:
                    # Фиксированный режим: чистый ТОЛЬКО выбранный основной
                    should_shade = (idx != self.selected_primary_idx)

                ov.apply_shade(should_shade, lvl)

    def toggle_dimmer(self):
        new_state = not self.dimmer_active.get()
        self.dimmer_active.set(new_state)

        if new_state:
            self.lbl_status.config(text="SENTINEL FOCUS ACTIVE", fg=COLOR_CYAN)
            self.lbl_dim_info.config(text="[ ФОКУС: ВКЛ ]", fg=COLOR_GREEN)
            self.btn_toggle.config(bg=COLOR_RED, text="⚡ Выключить Фокус")
            self._update_overlay_states()
            self.log("Focus Shade активирован.")
        else:
            self.lbl_status.config(text="SENTINEL DECK ACTIVE", fg=COLOR_GREEN)
            self.lbl_dim_info.config(text="[ ФОКУС: ВЫКЛ ]", fg=TEXT_MUTED)
            self.btn_toggle.config(bg=COLOR_BLUE, text="⚡ Включить Фокус")
            self._update_overlay_states()
            self.log("Focus Shade выключен: все мониторы открыты.")

    # --------------------------------------------------------------------------
    # ДВИЖОК БИНДОВ (КЛАВИАТУРА + МЫШЬ)
    # --------------------------------------------------------------------------
    def _normalize_key(self, key) -> str:
        if isinstance(key, keyboard.Key):
            k = key.name.upper()
            if "CTRL" in k: return "CTRL"
            if "SHIFT" in k: return "SHIFT"
            if "ALT" in k: return "ALT"
            return k
        if hasattr(key, "vk") and key.vk:
            vk = key.vk
            if 0x70 <= vk <= 0x87: return f"F{vk - 0x70 + 1}"
            if 0x30 <= vk <= 0x39: return chr(vk)
            if 0x41 <= vk <= 0x5A: return chr(vk)
        return str(key).replace("'", "").upper()

    def _start_listening_combo(self):
        if self.is_listening_combo:
            return
        self.is_listening_combo = True
        self.collected_combo.clear()
        self.btn_bind.config(text="[ Зажмите бинд... ]", bg=COLOR_CYAN, fg="#000000")
        self.log("Режим назначения: зажмите комбинацию на клавиатуре или мыши...")

    def _finish_listening_combo(self):
        if not self.collected_combo:
            self.is_listening_combo = False
            self.btn_bind.config(text=f"⌨ БИНД: {self.current_combo}", bg=COLOR_AMBER, fg="#000000")
            return

        order = {"CTRL": 1, "ALT": 2, "SHIFT": 3, "MOUSE4": 4, "MOUSE5": 5}
        sorted_keys = sorted(list(self.collected_combo), key=lambda k: (order.get(k, 10), k))
        combo_str = " + ".join(sorted_keys)

        self.current_combo = combo_str
        self.combo_label_var.set(f"⌨ БИНД: {combo_str}")
        self.lbl_cmd_hint.config(text=f" готов к работе. Бинд: {combo_str}")
        self.btn_bind.config(text=f"⌨ БИНД: {combo_str}", bg=COLOR_AMBER, fg="#000000")
        self.is_listening_combo = False
        self.collected_combo.clear()
        self.log(f"Назначена комбинация: {combo_str}")

    def _start_input_engine(self):
        def on_press(key):
            try:
                norm = self._normalize_key(key)
                self.currently_pressed.add(norm)

                if self.is_listening_combo:
                    self.collected_combo.add(norm)
                    self.btn_bind.config(text=" + ".join(sorted(self.collected_combo)))
                    return

                target = set(p.strip() for p in self.current_combo.split("+"))
                if target and target.issubset(self.currently_pressed):
                    self.after(0, self.toggle_dimmer)
            except Exception:
                pass

        def on_release(key):
            try:
                norm = self._normalize_key(key)
                if norm in self.currently_pressed:
                    self.currently_pressed.remove(norm)
                if self.is_listening_combo:
                    self.after(100, self._finish_listening_combo)
            except Exception:
                pass

        def on_click(x, y, button, pressed):
            try:
                b_str = str(button).replace("Button.", "").lower()
                m_map = {
                    "middle": "MOUSE_MID",
                    "x1": "MOUSE4",
                    "x2": "MOUSE5"
                }
                mapped = m_map.get(b_str)
                if not mapped:
                    return

                if pressed:
                    self.currently_pressed.add(mapped)
                    if self.is_listening_combo:
                        self.collected_combo.add(mapped)
                        self.btn_bind.config(text=" + ".join(sorted(self.collected_combo)))
                        self.after(350, self._finish_listening_combo)
                        return

                    target = set(p.strip() for p in self.current_combo.split("+"))
                    if target and target.issubset(self.currently_pressed):
                        self.after(0, self.toggle_dimmer)
                else:
                    if mapped in self.currently_pressed:
                        self.currently_pressed.remove(mapped)
            except Exception:
                pass

        keyboard_listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        keyboard_listener.daemon = True
        keyboard_listener.start()

        mouse_listener = mouse.Listener(on_click=on_click)
        mouse_listener.daemon = True
        mouse_listener.start()

    def _mouse_tracker(self):
        pt = POINT()
        while self.mouse_worker_running:
            user32.GetCursorPos(ctypes.byref(pt))
            cx, cy = pt.x, pt.y

            found_idx = None
            for idx, m in enumerate(self.monitors):
                if (m["x"] <= cx < m["x"] + m["w"]) and (m["y"] <= cy < m["y"] + m["h"]):
                    found_idx = idx
                    break

            if found_idx is not None and found_idx != self.current_mouse_mon_idx:
                self.current_mouse_mon_idx = found_idx
                self.after(0, self._draw_monitor_layout)

                # Если включен фокус и режим строгого следования — переключаем затемнение вслед за мышью
                if self.dimmer_active.get() and self.follow_mouse_strict.get():
                    self.after(0, self._update_overlay_states)

            time.sleep(0.04)

    def _check_autostart(self) -> bool:
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ) as key:
                winreg.QueryValueEx(key, "SentinelFocusShade")
                return True
        except Exception:
            return False

    def _toggle_autostart(self):
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        exe_path = f'"{sys.executable}" "{Path(__file__).resolve()}"'
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
                if not self.autostart_var.get():
                    winreg.SetValueEx(key, "SentinelFocusShade", 0, winreg.REG_SZ, exe_path)
                    self.autostart_var.set(True)
                    self.btn_autostart.config(text="🚀 АВТОЗАПУСК: [ВКЛ]", fg=COLOR_GREEN)
                    self.log("Автозапуск активирован.")
                else:
                    try:
                        winreg.DeleteValue(key, "SentinelFocusShade")
                    except FileNotFoundError:
                        pass
                    self.autostart_var.set(False)
                    self.btn_autostart.config(text="🚀 АВТОЗАПУСК: [ВЫКЛ]", fg=TEXT_MUTED)
                    self.log("Автозапуск отключен.")
        except Exception as ex:
            messagebox.showerror("Autostart Error", f"Ошибка реестра: {ex}")

    def _setup_tray(self):
        icon_img = create_circular_icon()
        menu = pystray.Menu(
            pystray.MenuItem("Показать окно", self.show_from_tray, default=True),
            pystray.MenuItem("Вкл/Выкл затемнение", lambda: self.after(0, self.toggle_dimmer)),
            pystray.MenuItem("Выход", self.quit_completely)
        )
        self.tray_icon = pystray.Icon("SentinelFocusShade", icon_img, "Sentinel Focus Shade", menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def hide_to_tray(self):
        self.withdraw()
        self.log("Окно свернуто в системный трей.")

    def show_from_tray(self):
        self.after(0, self.deiconify)
        self.after(0, self.lift)
        self.after(0, self.focus_force)

    def quit_completely(self):
        self.mouse_worker_running = False
        for ov in self.persistent_overlays:
            try:
                ov.destroy()
            except Exception:
                pass
        if self.tray_icon:
            try:
                self.tray_icon.stop()
            except Exception:
                pass
        if mutex:
            kernel32.CloseHandle(mutex)
        self.after(0, self.destroy)


# ------------------------------------------------------------------------------
# ТОЧКА ВХОДА (.pyw)
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    if sys.platform == "win32":
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

    app = SentinelDimmerApp()
    app.mainloop()