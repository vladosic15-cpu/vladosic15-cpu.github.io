"""
================================================================================
  SENTINEL OS :: FOCUS SHADE MATRIX v8.0 (OPERATOR EDITION)
  File Name: sentinel_focus_shade.pyw
  Stack: Python 3.10+ | Tkinter Matrix | WinAPI | pynput | pystray | Pillow
================================================================================
"""

import os
import sys
import io
import json
import time
import ctypes
from ctypes import wintypes
import threading
import subprocess
import tempfile
import winreg
from pathlib import Path
import tkinter as tk
from tkinter import messagebox

# 1. Защита от дубликатов процессов через системный мьютекс Windows
MUTEX_NAME = "Global\\SentinelFocusShadeMatrix_Mutex_V8"
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


def get_console_python_path() -> str:
    cur = Path(sys.executable)
    if cur.name.lower() == "pythonw.exe":
        cand = cur.parent / "python.exe"
        if cand.exists():
            return str(cand)
    return str(cur)


def ensure_dependencies():
    missing = []
    for mod_name, pkg_name in REQUIRED_PACKAGES.items():
        try:
            __import__(mod_name)
        except ImportError:
            missing.append(pkg_name)
    if missing:
        creationflags = 0x08000000 if sys.platform == "win32" else 0
        py_bin = get_console_python_path()
        for pkg in missing:
            try:
                subprocess.check_call(
                    [py_bin, "-m", "pip", "install", pkg, "--quiet"],
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
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Operator.SentinelOS.FocusShade.v8")
except Exception:
    pass

# Константы WinAPI
GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_NOACTIVATE = 0x08000000

HWND_TOPMOST = -1
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_NOACTIVATE = 0x0010

CONFIG_PATH = Path(tempfile.gettempdir()) / "sentinel_focus_shade_v8.json"

# Цветовая палитра Sentinel Deck
BG_DARK = "#050911"
BG_PANEL = "#0a1220"
BG_CARD = "#0f1c30"
BG_ACTIVE = "#153259"
BORDER_CLR = "#1e293b"
BORDER_NEON = "#38bdf8"

COLOR_CYAN = "#38bdf8"
COLOR_GREEN = "#10b981"
COLOR_RED = "#f43f5e"
COLOR_AMBER = "#f59e0b"
COLOR_PURPLE = "#a855f7"
COLOR_BLUE = "#0284c7"
TEXT_WHITE = "#f8fafc"
TEXT_MUTED = "#64748b"
TERMINAL_GREEN = "#34d399"

FONT_CONSOLE = ("Consolas", 9)
FONT_CONSOLE_BOLD = ("Consolas", 9, "bold")
FONT_TITLE = ("Consolas", 11, "bold")
FONT_STATUS = ("Consolas", 10, "bold")
FONT_MON_NAME = ("Consolas", 14, "bold")

# Режимы цветовых фильтров затемнения
SHADE_TINTS = {
    "Pitch Black (Чёрный)": "#000000",
    "Eye Care (Тёплый янтарь)": "#1a0d00",
    "Cyber Midnight (Синий)": "#020817",
    "Matrix Tint (Изумруд)": "#02140a"
}

# Индивидуальные режимы мониторов (ПКМ)
MON_MODE_AUTO = 0         # Подчиняется общим правилам
MON_MODE_ALWAYS_DARK = 1  # Всегда затемнен (даже с курсором)
MON_MODE_ALWAYS_LIT = 2   # Всегда яркий (никогда не затемняется)


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


class DEVMODEW(ctypes.Structure):
    _fields_ = [
        ("dmDeviceName", wintypes.WCHAR * 32),
        ("dmSpecVersion", wintypes.WORD),
        ("dmDriverVersion", wintypes.WORD),
        ("dmSize", wintypes.WORD),
        ("dmDriverExtra", wintypes.WORD),
        ("dmFields", wintypes.DWORD),
        ("dmPositionX", ctypes.c_long),
        ("dmPositionY", ctypes.c_long),
        ("dmDisplayOrientation", wintypes.DWORD),
        ("dmDisplayFixedOutput", wintypes.DWORD),
        ("dmColor", ctypes.c_short),
        ("dmDuplex", ctypes.c_short),
        ("dmYResolution", ctypes.c_short),
        ("dmTTOption", ctypes.c_short),
        ("dmCollate", ctypes.c_short),
        ("dmFormName", wintypes.WCHAR * 32),
        ("dmLogPixels", wintypes.WORD),
        ("dmBitsPerPel", wintypes.DWORD),
        ("dmPelsWidth", wintypes.DWORD),
        ("dmPelsHeight", wintypes.DWORD),
        ("dmDisplayFlags", wintypes.DWORD),
        ("dmDisplayFrequency", wintypes.DWORD),
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

            # Получаем герцовку монитора (Hz)
            hz = 60
            dm = DEVMODEW()
            dm.dmSize = ctypes.sizeof(DEVMODEW)
            if user32.EnumDisplaySettingsW(adapter_name, -1, ctypes.byref(dm)):
                if dm.dmDisplayFrequency > 0:
                    hz = dm.dmDisplayFrequency

            monitors.append({
                "device": adapter_name,
                "friendly_name": friendly_name,
                "x": rc.left,
                "y": rc.top,
                "w": rc.right - rc.left,
                "h": rc.bottom - rc.top,
                "hz": hz,
                "is_hw_primary": is_hardware_primary
            })
        return True

    ENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HMONITOR, wintypes.HDC, ctypes.POINTER(RECT), wintypes.LPARAM)
    user32.EnumDisplayMonitors(None, None, ENUMPROC(monitor_enum_proc), 0)
    return monitors


def make_window_click_through(hwnd: int):
    try:
        style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        style |= WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
    except Exception:
        pass


def create_circular_icon(active=False):
    img = Image.new("RGBA", (64, 64), color=(0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    outer_c = "#38bdf8" if active else "#10b981"
    inner_c = "#10b981" if active else "#38bdf8"
    draw.ellipse((2, 2, 62, 62), fill="#0a1322", outline=outer_c, width=4)
    draw.ellipse((12, 12, 52, 52), fill="#050a12", outline=inner_c, width=2)
    draw.ellipse((24, 24, 40, 40), fill=outer_c)
    return img


# ------------------------------------------------------------------------------
# ПОСТОЯННЫЙ ОВЕРЛЕЙ ЗАТЕМНЕНИЯ С ПЛАВНОЙ ИНТЕРПОЛЯЦИЕЙ (SMOOTH FADE)
# ------------------------------------------------------------------------------
class PersistentDimmer(tk.Toplevel):
    def __init__(self, master, mon, tint_color="#000000"):
        super().__init__(master)
        self.mon = mon
        self.current_alpha = 0.0
        self.target_alpha = 0.0
        self.hwnd = None

        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(bg=tint_color)

        self.geometry(f"{mon['w']}x{mon['h']}+{mon['x']}+{mon['y']}")
        self.attributes("-alpha", 0.0)

        self.update_idletasks()
        try:
            self.hwnd = user32.GetParent(self.winfo_id()) or self.winfo_id()
            make_window_click_through(self.hwnd)
        except Exception:
            pass

    def set_tint(self, color_hex: str):
        try:
            self.configure(bg=color_hex)
        except Exception:
            pass

    def enforce_topmost(self):
        """Удерживает оверлей поверх окон без перехвата фокуса."""
        if self.hwnd and self.current_alpha > 0.01:
            try:
                user32.SetWindowPos(
                    self.hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                    SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE
                )
            except Exception:
                pass

    def set_target_shade(self, state: bool, alpha: float, instant: bool = False):
        self.target_alpha = alpha if state else 0.0
        if instant:
            self.current_alpha = self.target_alpha
            try:
                self.attributes("-alpha", self.current_alpha)
            except Exception:
                pass

    def step_fade(self, speed: float = 0.16) -> bool:
        """Плавный шаг анимации прозрачности. Возвращает True, если еще в движении."""
        diff = self.target_alpha - self.current_alpha
        if abs(diff) < 0.015:
            if self.current_alpha != self.target_alpha:
                self.current_alpha = self.target_alpha
                try:
                    self.attributes("-alpha", self.current_alpha)
                except Exception:
                    pass
            return False

        self.current_alpha += diff * speed
        try:
            self.attributes("-alpha", round(self.current_alpha, 3))
        except Exception:
            pass
        return True


# ------------------------------------------------------------------------------
# ГЛАВНОЕ ОКНО CYBER DECK
# ------------------------------------------------------------------------------
class SentinelDimmerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Sentinel OS :: Focus Shade Matrix v8.0")
        self.geometry("960x680")
        self.minsize(840, 580)
        self.configure(bg=BG_DARK)

        self._apply_custom_app_icon()

        self.monitors = []
        self.persistent_overlays = []
        self.rendered_map_rects = []
        self.monitor_custom_modes = {}  # {mon_idx: MON_MODE_*}

        self.selected_primary_idx = 0
        self.current_mouse_mon_idx = 0

        # Состояния и настройки
        self.dimmer_active = tk.BooleanVar(value=False)
        self.follow_mouse_strict = tk.BooleanVar(value=True)
        self.smooth_fade_var = tk.BooleanVar(value=True)
        self.shade_level = tk.DoubleVar(value=0.80)
        self.selected_tint_name = tk.StringVar(value="Pitch Black (Чёрный)")
        self.autostart_var = tk.BooleanVar(value=self._check_autostart())

        # Бинды клавиш (с защитой от дребезга/автоповтора)
        self.current_combo = "F9"
        self.combo_label_var = tk.StringVar(value="⌨ БИНД: F9")
        self.is_listening_combo = False
        self.currently_pressed = set()
        self.collected_combo = set()
        self.combo_triggered_lock = False

        # История команд терминала
        self.cmd_history = []
        self.history_idx = -1

        self._load_config()
        self._setup_ui()
        self._refresh_monitors()
        self._start_input_engine()

        # Показываем окно
        self.deiconify()
        self.lift()
        self.attributes("-topmost", True)
        self.after(200, lambda: self.attributes("-topmost", False))
        self.focus_force()

        # Циклы анимации, плавного затухания и слежения за мышью
        self.pulse_phase = 0.0
        self._animate_status_pulse()
        self._smooth_fade_loop()
        self._z_order_watchdog_loop()

        self.mouse_worker_running = True
        self.thread_mouse = threading.Thread(target=self._mouse_tracker, daemon=True)
        self.thread_mouse.start()

        # Системный трей
        self.tray_icon = None
        self._setup_tray()

        self.protocol("WM_DELETE_WINDOW", self.hide_to_tray)

    # ── КОНФИГУРАЦИЯ (СОХРАНЕНИЕ ПРОФИЛЯ) ─────────────────────────────────
    def _load_config(self):
        if CONFIG_PATH.exists():
            try:
                data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
                self.shade_level.set(float(data.get("shade_level", 0.80)))
                self.follow_mouse_strict.set(bool(data.get("follow_mouse", True)))
                self.smooth_fade_var.set(bool(data.get("smooth_fade", True)))
                self.current_combo = str(data.get("combo", "F9"))
                self.combo_label_var.set(f"⌨ БИНД: {self.current_combo}")
                self.selected_primary_idx = int(data.get("primary_idx", 0))
                tint = data.get("tint_name", "Pitch Black (Чёрный)")
                if tint in SHADE_TINTS:
                    self.selected_tint_name.set(tint)
                raw_modes = data.get("custom_modes", {})
                self.monitor_custom_modes = {int(k): int(v) for k, v in raw_modes.items()}
            except Exception:
                pass

    def _save_config(self):
        try:
            data = {
                "shade_level": round(self.shade_level.get(), 2),
                "follow_mouse": self.follow_mouse_strict.get(),
                "smooth_fade": self.smooth_fade_var.get(),
                "combo": self.current_combo,
                "primary_idx": self.selected_primary_idx,
                "tint_name": self.selected_tint_name.get(),
                "custom_modes": self.monitor_custom_modes
            }
            CONFIG_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    def _apply_custom_app_icon(self):
        try:
            self.icon_image = create_circular_icon()
            temp_ico = Path(tempfile.gettempdir()) / "sentinel_focus_v8.ico"
            self.icon_image.save(temp_ico, format="ICO")
            self.iconbitmap(str(temp_ico))
        except Exception:
            pass

    # ── ПОСТРОЕНИЕ ИНТЕРФЕЙСА ─────────────────────────────────────────────
    def _setup_ui(self):
        # 1. Верхний статус-бар
        status_bar = tk.Frame(self, bg=BG_PANEL, padx=14, pady=8, highlightthickness=1, highlightbackground=BORDER_CLR)
        status_bar.pack(fill=tk.X, padx=14, pady=(10, 4))

        self.status_dot = tk.Canvas(status_bar, width=14, height=14, bg=BG_PANEL, highlightthickness=0)
        self.status_dot.pack(side=tk.LEFT, padx=(2, 8))

        self.lbl_status = tk.Label(
            status_bar, text="SENTINEL DECK READY", font=FONT_STATUS,
            bg=BG_PANEL, fg=COLOR_GREEN
        )
        self.lbl_status.pack(side=tk.LEFT)

        self.lbl_dim_info = tk.Label(
            status_bar, text="[ ФОКУС: ВЫКЛ ]", font=FONT_CONSOLE_BOLD,
            bg=BG_PANEL, fg=TEXT_MUTED
        )
        self.lbl_dim_info.pack(side=tk.LEFT, padx=16)

        self.lbl_mouse_coords = tk.Label(
            status_bar, text="XY: 0, 0 | Экран #1", font=FONT_CONSOLE,
            bg=BG_PANEL, fg=COLOR_CYAN
        )
        self.lbl_mouse_coords.pack(side=tk.LEFT, padx=10)

        self.btn_autostart = tk.Button(
            status_bar,
            text=f"🚀 АВТОЗАПУСК: [{'ВКЛ' if self.autostart_var.get() else 'ВЫКЛ'}]",
            font=FONT_CONSOLE_BOLD, bg=BG_CARD, fg=COLOR_GREEN if self.autostart_var.get() else TEXT_MUTED,
            bd=0, padx=12, pady=4, cursor="hand2",
            command=self._toggle_autostart
        )
        self.btn_autostart.pack(side=tk.RIGHT)

        # 2. Ряд оперативных кнопок и пресетов
        actions_bar = tk.Frame(self, bg=BG_DARK)
        actions_bar.pack(fill=tk.X, padx=14, pady=4)

        self.btn_toggle = self._create_btn(
            actions_bar, "⚡ Включить Фокус", COLOR_BLUE, TEXT_WHITE, self.toggle_dimmer
        )
        self.btn_toggle.pack(side=tk.LEFT, padx=(0, 6))

        btn_rescan = self._create_btn(
            actions_bar, "⟳ Скан дисплеев", BG_CARD, TEXT_WHITE, self._refresh_monitors
        )
        btn_rescan.pack(side=tk.LEFT, padx=4)

        self.btn_bind = tk.Button(
            actions_bar, textvariable=self.combo_label_var, font=FONT_CONSOLE_BOLD,
            bg=COLOR_AMBER, fg="#000000", bd=0, padx=12, pady=7, cursor="hand2",
            activebackground="#d97706", activeforeground=TEXT_WHITE,
            command=self._start_listening_combo
        )
        self.btn_bind.pack(side=tk.LEFT, padx=6)

        # Быстрые пресеты затемнения
        presets_frame = tk.Frame(actions_bar, bg=BG_DARK)
        presets_frame.pack(side=tk.LEFT, padx=10)
        tk.Label(presets_frame, text="Пресеты:", font=FONT_CONSOLE, bg=BG_DARK, fg=TEXT_MUTED).pack(side=tk.LEFT, padx=(0, 4))
        for pct, val in [("50%", 0.50), ("75%", 0.75), ("90%", 0.90), ("Blackout", 1.00)]:
            b = tk.Button(
                presets_frame, text=pct, font=FONT_CONSOLE_BOLD,
                bg=BG_PANEL, fg=COLOR_CYAN, bd=1, relief="solid",
                padx=7, pady=4, cursor="hand2",
                command=lambda v=val: self._apply_preset(v)
            )
            b.pack(side=tk.LEFT, padx=2)

        btn_tray = self._create_btn(
            actions_bar, "📥 В трей", COLOR_GREEN, "#000000", self.hide_to_tray
        )
        btn_tray.pack(side=tk.RIGHT)

        btn_gpu = self._create_btn(
            actions_bar, "⚡ Сброс GPU", "#7c2d12", "#fed7aa", self._restart_gpu_driver
        )
        btn_gpu.pack(side=tk.RIGHT, padx=6)

        # 3. Интерактивная матрица мониторов
        map_wrapper = tk.Frame(self, bg=BG_PANEL, highlightthickness=1, highlightbackground=BORDER_CLR)
        map_wrapper.pack(fill=tk.BOTH, expand=True, padx=14, pady=6)

        map_head = tk.Frame(map_wrapper, bg=BG_PANEL)
        map_head.pack(fill=tk.X, padx=12, pady=(8, 2))
        tk.Label(map_head, text="МАТРИЦА ДИСПЛЕЕВ WINDOWS", font=FONT_TITLE, bg=BG_PANEL, fg=COLOR_CYAN).pack(side=tk.LEFT)
        tk.Label(
            map_head,
            text="[ ЛКМ = Назначить основным | ПКМ = Режим экрана (Авто / Темный / Яркий) | Колесо = Уровень % ]",
            font=FONT_CONSOLE_BOLD, bg=BG_PANEL, fg=COLOR_GREEN
        ).pack(side=tk.RIGHT)

        self.canvas_map = tk.Canvas(map_wrapper, bg=BG_DARK, highlightthickness=0)
        self.canvas_map.pack(fill=tk.BOTH, expand=True, padx=8, pady=(4, 8))
        self.canvas_map.bind("<Configure>", lambda e: self._draw_monitor_layout())
        self.canvas_map.bind("<Button-1>", self._on_canvas_left_click)
        self.canvas_map.bind("<Button-3>", self._on_canvas_right_click)
        self.canvas_map.bind("<MouseWheel>", self._on_canvas_scroll)

        # 4. Панель тонкой настройки (Ползунок + Оттенок + Режимы)
        opt_bar = tk.Frame(self, bg=BG_PANEL, highlightthickness=1, highlightbackground=BORDER_CLR)
        opt_bar.pack(fill=tk.X, padx=14, pady=4)

        tk.Label(opt_bar, text="ЗАТЕМНЕНИЕ:", font=FONT_CONSOLE_BOLD, bg=BG_PANEL, fg=TEXT_WHITE).pack(side=tk.LEFT, padx=(12, 4), pady=8)
        self.lbl_slider_val = tk.Label(opt_bar, text=f"{int(self.shade_level.get() * 100)}%", font=FONT_CONSOLE_BOLD, bg=BG_PANEL, fg=COLOR_CYAN, width=4)
        self.lbl_slider_val.pack(side=tk.LEFT, padx=(0, 4))

        self.slider = tk.Scale(
            opt_bar, from_=0.15, to=1.00, resolution=0.05,
            orient=tk.HORIZONTAL, variable=self.shade_level, showvalue=False,
            bg=BG_PANEL, fg=COLOR_CYAN, highlightthickness=0,
            troughcolor=BG_DARK, activebackground=COLOR_GREEN, length=160,
            command=self._on_slider_change
        )
        self.slider.pack(side=tk.LEFT, padx=4)

        # Выбор оттенка (Цветовой фильтр)
        tk.Label(opt_bar, text="ФИЛЬТР:", font=FONT_CONSOLE_BOLD, bg=BG_PANEL, fg=TEXT_MUTED).pack(side=tk.LEFT, padx=(14, 4))
        tint_menu = tk.OptionMenu(opt_bar, self.selected_tint_name, *SHADE_TINTS.keys(), command=self._on_tint_change)
        tint_menu.config(
            bg=BG_CARD, fg=COLOR_CYAN, activebackground=BG_ACTIVE, activeforeground=TEXT_WHITE,
            font=FONT_CONSOLE_BOLD, bd=0, highlightthickness=1, highlightbackground=BORDER_CLR
        )
        tint_menu["menu"].config(bg=BG_PANEL, fg=COLOR_CYAN, font=FONT_CONSOLE)
        tint_menu.pack(side=tk.LEFT, padx=4)

        # Чекбокс плавного затухания
        chk_fade = tk.Checkbutton(
            opt_bar, text="Плавный переход",
            variable=self.smooth_fade_var, font=FONT_CONSOLE_BOLD,
            bg=BG_PANEL, fg=COLOR_GREEN, selectcolor=BG_DARK,
            activebackground=BG_PANEL, activeforeground=COLOR_GREEN,
            command=self._save_config
        )
        chk_fade.pack(side=tk.RIGHT, padx=(4, 10))

        # Переключатель: следовать за мышью
        chk_follow = tk.Checkbutton(
            opt_bar, text="Следовать за курсором",
            variable=self.follow_mouse_strict, font=FONT_CONSOLE_BOLD,
            bg=BG_PANEL, fg=COLOR_CYAN, selectcolor=BG_DARK,
            activebackground=BG_PANEL, activeforeground=COLOR_GREEN,
            command=self._on_follow_mode_toggle
        )
        chk_follow.pack(side=tk.RIGHT, padx=6)

        # 5. Интерактивный терминал Sentinel OS
        term_wrapper = tk.Frame(self, bg="#03060a", height=120, highlightthickness=1, highlightbackground="#143327")
        term_wrapper.pack(fill=tk.X, padx=14, pady=(4, 10))
        term_wrapper.pack_propagate(False)

        self.txt_terminal = tk.Text(
            term_wrapper, bg="#03060a", fg=TERMINAL_GREEN, font=FONT_CONSOLE,
            bd=0, padx=10, pady=6, wrap=tk.WORD, height=4
        )
        self.txt_terminal.pack(fill=tk.BOTH, expand=True)

        self.txt_terminal.tag_config("TIME", foreground="#475569")
        self.txt_terminal.tag_config("INFO", foreground="#34d399")
        self.txt_terminal.tag_config("SYS", foreground="#38bdf8")
        self.txt_terminal.tag_config("WARN", foreground="#facc15")
        self.txt_terminal.tag_config("SECRET", foreground="#c084fc", font=FONT_CONSOLE_BOLD)

        cmd_bar = tk.Frame(term_wrapper, bg="#06120d")
        cmd_bar.pack(side=tk.BOTTOM, fill=tk.X)
        tk.Label(cmd_bar, text="Operator@Sentinel:~$ ", font=FONT_CONSOLE_BOLD, bg="#06120d", fg=COLOR_GREEN).pack(side=tk.LEFT, padx=(8, 0), pady=3)

        self.cmd_entry = tk.Entry(
            cmd_bar, bg="#06120d", fg="#a7f3d0", insertbackground=COLOR_GREEN,
            relief="flat", font=FONT_CONSOLE
        )
        self.cmd_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4, pady=3)
        self.cmd_entry.bind("<Return>", self._on_terminal_enter)
        self.cmd_entry.bind("<Up>", self._history_up)
        self.cmd_entry.bind("<Down>", self._history_down)

    def _create_btn(self, parent, text, bg, fg, cmd):
        btn = tk.Button(
            parent, text=text, font=FONT_CONSOLE_BOLD,
            bg=bg, fg=fg, bd=0, padx=12, pady=7, cursor="hand2",
            activebackground="#1e3a5f", activeforeground=TEXT_WHITE,
            command=cmd
        )
        btn.default_bg = bg
        btn.bind("<Enter>", lambda e: btn.config(bg="#1e3a5f"))
        btn.bind("<Leave>", lambda e: btn.config(bg=btn.default_bg))
        return btn

    def log(self, text: str, tag: str = "INFO"):
        t_str = time.strftime("[%H:%M:%S]")
        self.txt_terminal.insert(tk.END, f"{t_str} ", "TIME")
        self.txt_terminal.insert(tk.END, f"{text}\n", tag)
        self.txt_terminal.see(tk.END)

    def _animate_status_pulse(self):
        self.pulse_phase += 0.15
        color = COLOR_CYAN if self.dimmer_active.get() else COLOR_GREEN
        self.status_dot.delete("all")
        self.status_dot.create_oval(
            2, 2, 12, 12, fill=color,
            outline=BORDER_NEON if self.dimmer_active.get() else "#059669", width=2
        )
        self.after(80, self._animate_status_pulse)

    def _apply_preset(self, val: float):
        self.shade_level.set(val)
        self.lbl_slider_val.config(text=f"{int(val * 100)}%")
        self._update_overlay_states()
        self._draw_monitor_layout()
        self._save_config()
        self.log(f"Применен пресет затемнения: {int(val * 100)}%", "SYS")

    def _on_slider_change(self, val):
        self.lbl_slider_val.config(text=f"{int(float(val) * 100)}%")
        self._update_overlay_states(instant=True)
        self._draw_monitor_layout()
        self._save_config()

    def _on_tint_change(self, tint_key):
        hex_clr = SHADE_TINTS.get(tint_key, "#000000")
        for ov in self.persistent_overlays:
            ov.set_tint(hex_clr)
        self._save_config()
        self.log(f"Установлен цветовой фильтр: {tint_key} ({hex_clr})", "SYS")

    def _on_follow_mode_toggle(self):
        if self.follow_mouse_strict.get():
            self.log("Режим: активен экран под курсором мыши (Dynamic Follow).", "SYS")
        else:
            self.log(f"Режим: зафиксирован основной экран #{self.selected_primary_idx + 1}.", "SYS")
        self._update_overlay_states()
        self._draw_monitor_layout()
        self._save_config()

    # --------------------------------------------------------------------------
    # ОТРИСОВКА ИНТЕРФЕЙСА КАРТЫ МОНИТОРОВ (С ГЕРЦОВКОЙ, РАЗРЕШЕНИЕМ И СТАТУСОМ)
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
        for x in range(0, c_w, 36):
            self.canvas_map.create_line(x, 0, x, c_h, fill="#09111d", width=1)
        for y in range(0, c_h, 36):
            self.canvas_map.create_line(0, y, c_w, y, fill="#09111d", width=1)

        min_x = min(m["x"] for m in self.monitors)
        max_x = max(m["x"] + m["w"] for m in self.monitors)
        min_y = min(m["y"] for m in self.monitors)
        max_y = max(m["y"] + m["h"] for m in self.monitors)

        total_w = max_x - min_x
        total_h = max_y - min_y
        if total_w <= 0 or total_h <= 0:
            return

        pad = 36
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
            custom_mode = self.monitor_custom_modes.get(idx, MON_MODE_AUTO)
            will_be_shaded = self._should_monitor_be_shaded(idx)

            # Определяем цвета карточки монитора
            if custom_mode == MON_MODE_ALWAYS_DARK:
                fill_clr = "#180b20"
                border_clr = COLOR_PURPLE
            elif custom_mode == MON_MODE_ALWAYS_LIT:
                fill_clr = "#0d281e"
                border_clr = COLOR_GREEN
            else:
                fill_clr = BG_ACTIVE if is_primary else BG_CARD
                border_clr = COLOR_GREEN if is_mouse_here else (COLOR_CYAN if is_primary else BORDER_CLR)

            border_w = 3 if (is_primary or is_mouse_here) else 1

            self.canvas_map.create_rectangle(
                rx1, ry1, rx2, ry2,
                fill=fill_clr, outline=border_clr, width=border_w
            )

            cx_mid = (rx1 + rx2) / 2
            cy_mid = (ry1 + ry2) / 2

            # 1. Имя и номер монитора
            self.canvas_map.create_text(
                cx_mid, cy_mid - 26,
                text=f"#{idx + 1} :: {m['friendly_name']}", font=FONT_CONSOLE_BOLD, fill=TEXT_WHITE
            )

            # 2. Разрешение и частота обновления (Hz)
            self.canvas_map.create_text(
                cx_mid, cy_mid - 6,
                text=f"{m['w']}x{m['h']} @ {m['hz']}Hz", font=FONT_CONSOLE, fill=COLOR_CYAN
            )

            # 3. Текущая роль и режим
            if custom_mode == MON_MODE_ALWAYS_DARK:
                role_txt = f"🔒 ВСЕГДА ТЕМНЫЙ ({int(self.shade_level.get()*100)}%)"
                role_clr = COLOR_PURPLE
            elif custom_mode == MON_MODE_ALWAYS_LIT:
                role_txt = "☀ ВСЕГДА ЯРКИЙ (БЕЗ ТЕМНОТЫ)"
                role_clr = COLOR_GREEN
            else:
                if is_mouse_here and self.follow_mouse_strict.get():
                    role_txt = "● АКТИВЕН [КУРСОР ЗДЕСЬ]"
                    role_clr = COLOR_GREEN
                elif is_primary and not self.follow_mouse_strict.get():
                    role_txt = "★ ОСНОВНОЙ [БЕЗ ТЕМНОТЫ]"
                    role_clr = COLOR_CYAN
                else:
                    pct = int(self.shade_level.get() * 100) if self.dimmer_active.get() and will_be_shaded else 0
                    role_txt = f"[ SHADE: {pct}% ]" if pct > 0 else "[ ОЖИДАНИЕ ФОКУСА ]"
                    role_clr = COLOR_AMBER if pct > 0 else TEXT_MUTED

            self.canvas_map.create_text(
                cx_mid, cy_mid + 16,
                text=role_txt, font=FONT_CONSOLE_BOLD, fill=role_clr
            )

            # 4. Метка Primary в углу экрана
            if is_primary:
                self.canvas_map.create_text(
                    rx1 + 10, ry1 + 10, anchor="nw",
                    text="PRIMARY", font=("Consolas", 8, "bold"), fill=COLOR_CYAN
                )

            self.rendered_map_rects.append({
                "idx": idx,
                "rect": (rx1, ry1, rx2, ry2),
                "mon": m
            })

    def _on_canvas_left_click(self, event):
        """ЛКМ — выбор основного дисплея."""
        cx, cy = event.x, event.y
        for item in self.rendered_map_rects:
            x1, y1, x2, y2 = item["rect"]
            if x1 <= cx <= x2 and y1 <= cy <= y2:
                idx = item["idx"]
                self.selected_primary_idx = idx
                self.log(f"Основным назначен дисплей #{idx + 1} ({item['mon']['friendly_name']})", "SYS")
                self._draw_monitor_layout()
                self._update_overlay_states()
                self._save_config()
                break

    def _on_canvas_right_click(self, event):
        """ПКМ — переключение индивидуального режима дисплея (Авто -> Всегда Темный -> Всегда Яркий)."""
        cx, cy = event.x, event.y
        for item in self.rendered_map_rects:
            x1, y1, x2, y2 = item["rect"]
            if x1 <= cx <= x2 and y1 <= cy <= y2:
                idx = item["idx"]
                cur = self.monitor_custom_modes.get(idx, MON_MODE_AUTO)
                nxt = (cur + 1) % 3
                self.monitor_custom_modes[idx] = nxt

                names = {
                    MON_MODE_AUTO: "АВТОМАТИЧЕСКИЙ",
                    MON_MODE_ALWAYS_DARK: "ВСЕГДА ТЕМНЫЙ (LOCK DARK)",
                    MON_MODE_ALWAYS_LIT: "ВСЕГДА ЯРКИЙ (LOCK LIT)"
                }
                self.log(f"Дисплей #{idx + 1}: режим переключен на [{names[nxt]}]", "WARN")
                self._draw_monitor_layout()
                self._update_overlay_states()
                self._save_config()
                break

    def _on_canvas_scroll(self, event):
        """Колесо мыши по карте меняет уровень затемнения с шагом 5%."""
        delta = 0.05 if event.delta > 0 else -0.05
        new_val = min(1.0, max(0.15, round(self.shade_level.get() + delta, 2)))
        self.shade_level.set(new_val)
        self.lbl_slider_val.config(text=f"{int(new_val * 100)}%")
        self._update_overlay_states(instant=True)
        self._draw_monitor_layout()
        self._save_config()

    # --------------------------------------------------------------------------
    # ЯДРО УПРАВЛЕНИЯ ЗАТЕМНЕНИЕМ И СТОРОЖЕВОЙ ТАЙМЕР ПОВЕРХ ОКОН
    # --------------------------------------------------------------------------
    def _should_monitor_be_shaded(self, idx: int) -> bool:
        if not self.dimmer_active.get():
            return False

        custom_mode = self.monitor_custom_modes.get(idx, MON_MODE_AUTO)
        if custom_mode == MON_MODE_ALWAYS_DARK:
            return True
        if custom_mode == MON_MODE_ALWAYS_LIT:
            return False

        if self.follow_mouse_strict.get():
            return idx != self.current_mouse_mon_idx
        else:
            return idx != self.selected_primary_idx

    def _refresh_monitors(self):
        for ov in self.persistent_overlays:
            try:
                ov.destroy()
            except Exception:
                pass
        self.persistent_overlays.clear()

        self.monitors = get_all_monitors()

        if self.selected_primary_idx >= len(self.monitors):
            self.selected_primary_idx = 0
            for idx, m in enumerate(self.monitors):
                if m["is_hw_primary"]:
                    self.selected_primary_idx = idx
                    break

        tint_hex = SHADE_TINTS.get(self.selected_tint_name.get(), "#000000")
        for m in self.monitors:
            self.persistent_overlays.append(PersistentDimmer(self, m, tint_hex))

        self.log(f"Сетка дисплеев инициализирована: {len(self.monitors)} шт.", "SYS")
        self.after(50, self._draw_monitor_layout)
        self._update_overlay_states(instant=True)

    def _update_overlay_states(self, instant: bool = False):
        lvl = self.shade_level.get()
        use_instant = instant or (not self.smooth_fade_var.get())

        for idx, ov in enumerate(self.persistent_overlays):
            should_shade = self._should_monitor_be_shaded(idx)
            ov.set_target_shade(should_shade, lvl, instant=use_instant)

    def _smooth_fade_loop(self):
        """Цикл плавной интерполяции прозрачности (~60 FPS)."""
        for ov in self.persistent_overlays:
            ov.step_fade(speed=0.22)
        self.after(16, self._smooth_fade_loop)

    def _z_order_watchdog_loop(self):
        """Удерживает затемнение поверх полноэкранных окон и панели задач."""
        if self.dimmer_active.get():
            for ov in self.persistent_overlays:
                ov.enforce_topmost()
        self.after(2500, self._z_order_watchdog_loop)

    def toggle_dimmer(self):
        new_state = not self.dimmer_active.get()
        self.dimmer_active.set(new_state)

        if new_state:
            self.lbl_status.config(text="SENTINEL FOCUS ACTIVE", fg=COLOR_CYAN)
            self.lbl_dim_info.config(text="[ ФОКУС: АКТИВЕН ]", fg=COLOR_GREEN)
            self.btn_toggle.default_bg = COLOR_RED
            self.btn_toggle.config(bg=COLOR_RED, text="⚡ Выключить Фокус")
            self.log("Focus Shade активирован.", "INFO")
        else:
            self.lbl_status.config(text="SENTINEL DECK READY", fg=COLOR_GREEN)
            self.lbl_dim_info.config(text="[ ФОКУС: ВЫКЛ ]", fg=TEXT_MUTED)
            self.btn_toggle.default_bg = COLOR_BLUE
            self.btn_toggle.config(bg=COLOR_BLUE, text="⚡ Включить Фокус")
            self.log("Focus Shade отключен: все мониторы яркие.", "WARN")

        self._update_overlay_states()
        self._draw_monitor_layout()
        if self.tray_icon:
            try:
                self.tray_icon.icon = create_circular_icon(active=new_state)
            except Exception:
                pass

    def _restart_gpu_driver(self):
        """Аппаратный сброс видеодрайвера Windows (Win+Ctrl+Shift+B)."""
        self.log("Послан сигнал перезапуска видеодрайвера (Win+Ctrl+Shift+B)...", "SYS")
        try:
            VK_LWIN, VK_CONTROL, VK_SHIFT, VK_B = 0x5B, 0x11, 0x10, 0x42
            KEYUP = 0x0002
            user32.keybd_event(VK_LWIN, 0, 0, 0)
            user32.keybd_event(VK_CONTROL, 0, 0, 0)
            user32.keybd_event(VK_SHIFT, 0, 0, 0)
            user32.keybd_event(VK_B, 0, 0, 0)
            time.sleep(0.05)
            user32.keybd_event(VK_B, 0, KEYUP, 0)
            user32.keybd_event(VK_SHIFT, 0, KEYUP, 0)
            user32.keybd_event(VK_CONTROL, 0, KEYUP, 0)
            user32.keybd_event(VK_LWIN, 0, KEYUP, 0)
            self.after(1500, self._refresh_monitors)
        except Exception as e:
            self.log(f"Ошибка сброса GPU: {e}", "WARN")

    # --------------------------------------------------------------------------
    # ТЕРМИНАЛ И КОМАНДЫ
    # --------------------------------------------------------------------------
    def _history_up(self, event):
        if self.cmd_history and self.history_idx > 0:
            self.history_idx -= 1
            self.cmd_entry.delete(0, tk.END)
            self.cmd_entry.insert(0, self.cmd_history[self.history_idx])
        return "break"

    def _history_down(self, event):
        if self.cmd_history and self.history_idx < len(self.cmd_history) - 1:
            self.history_idx += 1
            self.cmd_entry.delete(0, tk.END)
            self.cmd_entry.insert(0, self.cmd_history[self.history_idx])
        else:
            self.history_idx = len(self.cmd_history)
            self.cmd_entry.delete(0, tk.END)
        return "break"

    def _on_terminal_enter(self, event=None):
        raw = self.cmd_entry.get().strip()
        self.cmd_entry.delete(0, tk.END)
        if not raw:
            return

        self.cmd_history.append(raw)
        self.history_idx = len(self.cmd_history)
        self.log(f"Operator@Sentinel:~$ {raw}", "SYS")

        parts = raw.lower().split()
        cmd = parts[0]

        if cmd in ("help", "?"):
            self.log("Команды: focus (вкл/выкл) | set <15-100> | reset (сброс режимов экранов) | gpu | cls", "INFO")
        elif cmd == "focus":
            self.toggle_dimmer()
        elif cmd == "set" and len(parts) > 1:
            try:
                v = max(15, min(100, int(parts[1]))) / 100.0
                self._apply_preset(v)
            except ValueError:
                self.log("Укажите число от 15 до 100. Пример: set 85", "WARN")
        elif cmd == "reset":
            self.monitor_custom_modes.clear()
            self.currently_pressed.clear()
            self._draw_monitor_layout()
            self._update_overlay_states()
            self._save_config()
            self.log("Индивидуальные блокировки экранов и буфер клавиш сброшены.", "INFO")
        elif cmd == "gpu":
            self._restart_gpu_driver()
        elif cmd == "cls":
            self.txt_terminal.delete("1.0", tk.END)
        elif cmd in ("operator", "vladosic", "vladosic15"):
            self.log("★ [OPERATOR VERIFIED] Матрица трех дисплеев синхронизирована. Приятной работы!", "SECRET")
        elif cmd in ("rats", "принц", "толик"):
            self.log("★ Принц и Толик одобряют мягкий свет на мониторах! 🐀🐀", "SECRET")
        elif cmd in ("bioshock", "rapture"):
            self.log("★ [RAPTURE] «A man chooses, a slave obeys.»", "SECRET")
        else:
            self.log(f"Неизвестная команда '{cmd}'. Введите 'help'.", "WARN")

    # --------------------------------------------------------------------------
    # ДВИЖОК БИНДОВ С ЗАЩИТОЙ ОТ ДРЕБЕЗГА И ЗАЛИПАНИЯ
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
        self.currently_pressed.clear()
        self.btn_bind.config(text="[ Зажмите клавишу/мышь... ]", bg=COLOR_CYAN, fg="#000000")
        self.log("Назначение бинда: нажмите желаемую клавишу или боковую кнопку мыши...", "SYS")

    def _finish_listening_combo(self):
        if not self.is_listening_combo:
            return
        if not self.collected_combo:
            self.is_listening_combo = False
            self.btn_bind.config(text=f"⌨ БИНД: {self.current_combo}", bg=COLOR_AMBER, fg="#000000")
            return

        order = {"CTRL": 1, "ALT": 2, "SHIFT": 3, "MOUSE4": 4, "MOUSE5": 5}
        sorted_keys = sorted(list(self.collected_combo), key=lambda k: (order.get(k, 10), k))
        combo_str = " + ".join(sorted_keys)

        self.current_combo = combo_str
        self.combo_label_var.set(f"⌨ БИНД: {combo_str}")
        self.btn_bind.config(text=f"⌨ БИНД: {combo_str}", bg=COLOR_AMBER, fg="#000000")
        self.is_listening_combo = False
        self.collected_combo.clear()
        self._save_config()
        self.log(f"Сохранен новый бинд активации: {combo_str}", "INFO")

    def _start_input_engine(self):
        def on_press(key):
            try:
                norm = self._normalize_key(key)
                self.currently_pressed.add(norm)

                if self.is_listening_combo:
                    self.collected_combo.add(norm)
                    self.after(0, lambda: self.btn_bind.config(text=" + ".join(sorted(self.collected_combo))))
                    return

                target = set(p.strip() for p in self.current_combo.split("+"))
                if target and target.issubset(self.currently_pressed):
                    if not self.combo_triggered_lock:
                        self.combo_triggered_lock = True
                        self.after(0, self.toggle_dimmer)
            except Exception:
                pass

        def on_release(key):
            try:
                norm = self._normalize_key(key)
                self.currently_pressed.discard(norm)

                target = set(p.strip() for p in self.current_combo.split("+"))
                if not target.issubset(self.currently_pressed):
                    self.combo_triggered_lock = False

                if self.is_listening_combo and self.collected_combo:
                    self.after(120, self._finish_listening_combo)
            except Exception:
                pass

        def on_click(x, y, button, pressed):
            try:
                b_str = str(button).replace("Button.", "").lower()
                m_map = {"middle": "MOUSE_MID", "x1": "MOUSE4", "x2": "MOUSE5"}
                mapped = m_map.get(b_str)
                if not mapped:
                    return

                if pressed:
                    self.currently_pressed.add(mapped)
                    if self.is_listening_combo:
                        self.collected_combo.add(mapped)
                        self.after(0, lambda: self.btn_bind.config(text=" + ".join(sorted(self.collected_combo))))
                        self.after(300, self._finish_listening_combo)
                        return

                    target = set(p.strip() for p in self.current_combo.split("+"))
                    if target and target.issubset(self.currently_pressed):
                        if not self.combo_triggered_lock:
                            self.combo_triggered_lock = True
                            self.after(0, self.toggle_dimmer)
                else:
                    self.currently_pressed.discard(mapped)
                    target = set(p.strip() for p in self.current_combo.split("+"))
                    if not target.issubset(self.currently_pressed):
                        self.combo_triggered_lock = False
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
        tick_counter = 0
        while self.mouse_worker_running:
            user32.GetCursorPos(ctypes.byref(pt))
            cx, cy = pt.x, pt.y

            found_idx = None
            for idx, m in enumerate(self.monitors):
                if (m["x"] <= cx < m["x"] + m["w"]) and (m["y"] <= cy < m["y"] + m["h"]):
                    found_idx = idx
                    break

            tick_counter += 1
            if tick_counter % 3 == 0:
                m_num = (found_idx + 1) if found_idx is not None else 1
                self.after(0, lambda x=cx, y=cy, n=m_num: self.lbl_mouse_coords.config(text=f"XY: {x}, {y} | Экран #{n}"))

            if found_idx is not None and found_idx != self.current_mouse_mon_idx:
                self.current_mouse_mon_idx = found_idx
                self.after(0, self._draw_monitor_layout)

                if self.dimmer_active.get() and self.follow_mouse_strict.get():
                    self.after(0, self._update_overlay_states)

            time.sleep(0.035)

    # --------------------------------------------------------------------------
    # АВТОЗАПУСК И СИСТЕМНЫЙ ТРЕЙ
    # --------------------------------------------------------------------------
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
        pyw = Path(sys.executable).parent / "pythonw.exe"
        exec_bin = pyw if pyw.exists() else Path(sys.executable)
        exe_path = f'"{exec_bin}" "{Path(__file__).resolve()}"'

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
                if not self.autostart_var.get():
                    winreg.SetValueEx(key, "SentinelFocusShade", 0, winreg.REG_SZ, exe_path)
                    self.autostart_var.set(True)
                    self.btn_autostart.config(text="🚀 АВТОЗАПУСК: [ВКЛ]", fg=COLOR_GREEN)
                    self.log("Автозапуск Windows включен (через pythonw).", "INFO")
                else:
                    try:
                        winreg.DeleteValue(key, "SentinelFocusShade")
                    except FileNotFoundError:
                        pass
                    self.autostart_var.set(False)
                    self.btn_autostart.config(text="🚀 АВТОЗАПУСК: [ВЫКЛ]", fg=TEXT_MUTED)
                    self.log("Автозапуск Windows отключен.", "WARN")
        except Exception as ex:
            messagebox.showerror("Autostart Error", f"Ошибка реестра: {ex}")

    def _setup_tray(self):
        icon_img = create_circular_icon(active=False)
        menu = pystray.Menu(
            pystray.MenuItem("Развернуть Focus Matrix", self.show_from_tray, default=True),
            pystray.MenuItem("Вкл/Выкл Фокус", lambda: self.after(0, self.toggle_dimmer)),
            pystray.MenuItem("Пресет: 50%", lambda: self.after(0, lambda: self._apply_preset(0.50))),
            pystray.MenuItem("Пресет: 85%", lambda: self.after(0, lambda: self._apply_preset(0.85))),
            pystray.MenuItem("Пресет: 100% (Blackout)", lambda: self.after(0, lambda: self._apply_preset(1.00))),
            pystray.MenuItem("Сброс GPU драйвера", lambda: self.after(0, self._restart_gpu_driver)),
            pystray.MenuItem("Выход", self.quit_completely)
        )
        self.tray_icon = pystray.Icon("SentinelFocusShade", icon_img, "Sentinel Focus Shade v8.0", menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def hide_to_tray(self):
        self._save_config()
        self.withdraw()
        self.log("Интерфейс свернут в системный трей.", "SYS")

    def show_from_tray(self):
        self.after(0, self.deiconify)
        self.after(0, self.lift)
        self.after(0, self.focus_force)

    def quit_completely(self):
        self._save_config()
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
            ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Per-Monitor DPI Aware v2
        except Exception:
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(1)
            except Exception:
                pass

    app = SentinelDimmerApp()
    app.mainloop()
