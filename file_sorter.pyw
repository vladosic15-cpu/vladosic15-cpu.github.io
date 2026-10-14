import os
import sys
import json
import subprocess
import shutil
import time
import threading
import winreg
import tempfile
import hashlib
import math
import socket
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox

# Регистрация AppUserModelID для корректной иконки в панели задач Windows
try:
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Operator.SentinelOS.Core.5.0")
except Exception:
    pass

# Ограничение одного экземпляра через локальный сокет
SINGLE_INSTANCE_PORT = 49201
try:
    _instance_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    _instance_socket.bind(('127.0.0.1', SINGLE_INSTANCE_PORT))
except OSError:
    sys.exit(0)

APP_NAME = "Sentinel OS v5.0"
TARGET_DIR = Path.home() / "Downloads"
RECENT_FOLDER_NAME = "Недавнее"
QUARANTINE_FOLDER_NAME = "Quarantine"
CONFIG_FILE = Path(tempfile.gettempdir()) / "sentinel_os_config.json"

CATEGORIES = {
    "Аудио и Сэмплы": [".mp3", ".wav", ".flac", ".ogg", ".mid", ".aac", ".m4a"],
    "Проекты FL и Графика": [".flp", ".fst", ".fsc", ".psd", ".kra", ".ai", ".eps", ".svg"],
    "Архивы и Образы": [".zip", ".rar", ".7z", ".tar", ".gz", ".iso", ".torrent"],
    "Изображения": [".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".ico"],
    "Видео": [".mp4", ".mkv", ".avi", ".mov", ".webm", ".wmv"],
    "Программы и Скрипты": [".exe", ".msi", ".msixbundle", ".bat", ".cmd", ".ps1", ".py", ".reg", ".apk"],
    "Документы и Таблицы": [".pdf", ".docx", ".doc", ".txt", ".xlsx", ".xls", ".xlsm", ".pptx", ".csv", ".cer", ".rtf"],
    "Моды Minecraft": [".jar", ".mrpack", ".mcpack", ".mcworld"],
}

TEMP_EXTENSIONS = {".crdownload", ".part", ".tmp", ".download", ".opdownload"}
IGNORED_FILES = {"desktop.ini", "thumbs.db", ".ds_store", ".sentinel_meta.json"}
AUTORUN_REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"

MALICIOUS_PATTERNS = [
    b"powershell -w hidden",
    b"powershell -windowstyle hidden",
    b"downloadstring",
    b"frombase64string",
    b"bitsadmin /transfer",
    b"certutil -urlcache",
    b"set-mppreference -disablerealtime",
    b"vssadmin delete shadows",
    b"reg add hkcu\\software\\microsoft\\windows\\currentversion\\run",
    b"rundll32.exe javascript:",
    b"invoke-webrequest -usebasicparsing",
    b"invoke-expression",
    b"amsiutils"
]


def get_console_python_path() -> str:
    cur = Path(sys.executable)
    if cur.name.lower() == "pythonw.exe":
        cand = cur.parent / "python.exe"
        if cand.exists():
            return str(cand)
    return str(cur)


def get_accurate_os_name() -> str:
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion") as key:
            prod_name, _ = winreg.QueryValueEx(key, "ProductName")
            build_str, _ = winreg.QueryValueEx(key, "CurrentBuild")
            build = int(build_str)
            disp_ver = ""
            try:
                disp_ver, _ = winreg.QueryValueEx(key, "DisplayVersion")
            except FileNotFoundError:
                pass
            if build >= 22000:
                prod_name = prod_name.replace("Windows 10", "Windows 11")
            ver_part = f" ({disp_ver})" if disp_ver else ""
            return f"{prod_name}{ver_part} [Build {build}]"
    except Exception:
        build = sys.getwindowsversion().build
        win_ver = "Windows 11" if build >= 22000 else "Windows 10"
        return f"{win_ver} [Build {build}]"


def get_cpu_brand_name() -> str:
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0") as key:
            name, _ = winreg.QueryValueEx(key, "ProcessorNameString")
            return name.strip()
    except Exception:
        return os.environ.get("PROCESSOR_IDENTIFIER", "CPU")


def generate_app_icon_file() -> str:
    ico_path = os.path.join(tempfile.gettempdir(), "sentinel_badge_v5.ico")
    try:
        from PIL import Image, ImageDraw
        img = Image.new("RGBA", (64, 64), color=(0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.polygon([(32, 4), (60, 18), (52, 54), (32, 62), (12, 54), (4, 18)], fill="#090d16", outline="#38bdf8", width=3)
        d.polygon([(32, 14), (48, 22), (42, 46), (32, 52), (22, 46), (16, 22)], fill="#0284c7")
        d.ellipse([(27, 27), (37, 37)], fill="#34d399", outline="#ffffff", width=1)
        img.save(ico_path, format="ICO", sizes=[(64, 64), (32, 32), (16, 16)])
        return ico_path
    except Exception:
        return ""


class NatureRelaxWindow:
    """Анимированная сцена отдыха с облаками и солнцем."""
    def __init__(self, parent):
        self.win = tk.Toplevel(parent)
        self.win.title("Sentinel OS — Зона Спокойствия")
        self.win.geometry("680x500")
        self.win.configure(bg="#070c12")
        self.win.resizable(False, False)
        self.win.attributes("-topmost", True)

        self.canvas = tk.Canvas(self.win, width=680, height=500, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Небо
        self.canvas.create_rectangle(0, 0, 680, 270, fill="#0ea5e9", outline="")
        self.canvas.create_rectangle(0, 0, 680, 110, fill="#0284c7", outline="")

        # Солнце
        sx, sy, r = 95, 85, 36
        self.sun_rays = []
        for angle in range(0, 360, 30):
            rad = math.radians(angle)
            line = self.canvas.create_line(
                sx + math.cos(rad)*(r+5), sy + math.sin(rad)*(r+5),
                sx + math.cos(rad)*(r+22), sy + math.sin(rad)*(r+22),
                fill="#fde047", width=3
            )
            self.sun_rays.append(line)
        self.canvas.create_oval(sx - r, sy - r, sx + r, sy + r, fill="#facc15", outline="#fef08a", width=2)

        # Облака
        self.clouds = []
        for cx, cy in [(180, 70), (215, 65), (250, 70), (470, 95), (505, 90), (540, 95)]:
            ov = self.canvas.create_oval(cx-28, cy-18, cx+28, cy+18, fill="#f8fafc", outline="")
            self.clouds.append(ov)

        # Холмы и поляна
        self.canvas.create_oval(-90, 175, 430, 390, fill="#15803d", outline="")
        self.canvas.create_oval(250, 180, 770, 395, fill="#166534", outline="")
        self.canvas.create_rectangle(0, 260, 680, 500, fill="#16a34a", outline="")

        # Река
        river_points = [
            (310, 255), (350, 255), (400, 320), (450, 380), (440, 440), (400, 500),
            (295, 500), (325, 430), (315, 360), (280, 300)
        ]
        self.canvas.create_polygon(river_points, fill="#0284c7", outline="#38bdf8", width=2, smooth=True)

        # Цветы
        for fx, fy in [(65, 330), (130, 400), (195, 310), (240, 440), (540, 340), (600, 410), (500, 460)]:
            self.canvas.create_oval(fx-4, fy-4, fx+4, fy+4, fill="#f43f5e", outline="")
            self.canvas.create_oval(fx-1.5, fy-1.5, fx+1.5, fy+1.5, fill="#fef08a", outline="")

        self.canvas.create_rectangle(140, 445, 540, 485, fill="#09131c", outline="#38bdf8", width=1)
        self.canvas.create_text(
            340, 465,
            text="✨ Всё под контролем, Operator. Рабочий стол чист ✨",
            fill="#f8fafc", font=("Segoe UI", 10, "bold")
        )

        self._animate_clouds()

    def _animate_clouds(self):
        if not self.win.winfo_exists():
            return
        for c in self.clouds:
            self.canvas.move(c, 0.35, 0)
            coords = self.canvas.coords(c)
            if coords and coords[0] > 700:
                self.canvas.move(c, -760, 0)
        self.win.after(50, self._animate_clouds)


class HardwareDiagWindow:
    def __init__(self, parent):
        self.win = tk.Toplevel(parent)
        self.win.title("Sentinel OS — Аппаратная Телеметрия")
        self.win.geometry("720x580")
        self.win.configure(bg="#060a10")
        self.win.resizable(False, False)
        self.win.attributes("-topmost", True)

        header = tk.Frame(self.win, bg="#0d1826", padx=16, pady=12, highlightthickness=1, highlightbackground="#1e344f")
        header.pack(fill=tk.X, padx=10, pady=(10, 0))

        tk.Label(
            header,
            text="⚡ АППАРАТНАЯ ТЕЛЕМЕТРИЯ И ДИАГНОСТИКА УЗЛОВ",
            fg="#38bdf8",
            bg="#0d1826",
            font=("Consolas", 12, "bold")
        ).pack(side=tk.LEFT)

        tk.Button(
            header,
            text="🔄 Обновить",
            bg="#0284c7",
            fg="#ffffff",
            relief="flat",
            font=("Segoe UI", 9, "bold"),
            padx=10,
            cursor="hand2",
            command=self._load_specs
        ).pack(side=tk.RIGHT)

        self.text_box = tk.Text(
            self.win,
            bg="#04070b",
            fg="#34d399",
            font=("Consolas", 10),
            relief="flat",
            padx=16,
            pady=14,
            highlightthickness=1,
            highlightbackground="#14293a"
        )
        self.text_box.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self._load_specs()

    def _load_specs(self):
        self.text_box.delete("1.0", tk.END)
        self.text_box.insert(tk.END, "Сбор аппаратных метрик...\n")
        threading.Thread(target=self._gather_specs_thread, daemon=True).start()

    def _gather_specs_thread(self):
        specs = []
        specs.append(f"╔══ СИСТЕМА И ЯДРО ══════════════════════════════════════════════╗")
        specs.append(f"  • ОС:          {get_accurate_os_name()}")
        specs.append(f"  • Архитектура: {os.environ.get('PROCESSOR_ARCHITECTURE', 'AMD64')}")
        specs.append(f"  • Имя узла:    {socket.gethostname()}")

        try:
            import psutil
            cpu_name = get_cpu_brand_name()
            cores = psutil.cpu_count(logical=False)
            threads = psutil.cpu_count(logical=True)
            usage = psutil.cpu_percent(interval=0.2)
            freq = psutil.cpu_freq()
            freq_str = f" | Частота: {int(freq.current)} MHz" if freq else ""

            specs.append(f"\n╔══ ПРОЦЕССОР (CPU) ═════════════════════════════════════════════╗")
            specs.append(f"  • Модель:      {cpu_name}")
            specs.append(f"  • Конфиг:      {cores} Ядер / {threads} Потоков{freq_str}")
            specs.append(f"  • Нагрузка:    {usage}%")

            ram = psutil.virtual_memory()
            swap = psutil.swap_memory()
            specs.append(f"\n╔══ ПАМЯТЬ (RAM & SWAP) ═════════════════════════════════════════╗")
            specs.append(f"  • Всего ОЗУ:   {round(ram.total / (1024**3), 2)} GB")
            specs.append(f"  • Доступно:    {round(ram.available / (1024**3), 2)} GB (Занято: {ram.percent}%)")
            specs.append(f"  • Файл подкачки: {round(swap.used / (1024**3), 2)} GB / {round(swap.total / (1024**3), 2)} GB")

            specs.append(f"\n╔══ НАКОПИТЕЛИ (STORAGE) ════════════════════════════════════════╗")
            for part in psutil.disk_partitions(all=False):
                try:
                    u = psutil.disk_usage(part.mountpoint)
                    bar_len = 16
                    filled = int((u.percent / 100) * bar_len)
                    bar = "█" * filled + "░" * (bar_len - filled)
                    specs.append(
                        f"  • Диск {part.device:3} [{part.fstype:4}] [{bar}] {u.percent:4}% | "
                        f"Свободно: {u.free // (1024**3):4} GB из {u.total // (1024**3):4} GB"
                    )
                except PermissionError:
                    continue
        except ImportError:
            specs.append("\n[!] Модуль psutil еще загружается...")

        specs.append(f"\n╔══ ГРАФИЧЕСКАЯ ПОДСИСТЕМА И МОНИТОРЫ ═══════════════════════════╗")
        try:
            cmd = (
                "powershell -NoProfile -Command "
                "\"Get-CimInstance Win32_VideoController | ForEach-Object { $_.Name + ' (' + [math]::Round($_.AdapterRAM/1GB, 1) + ' GB)' }\""
            )
            gpu_out = subprocess.check_output(cmd, shell=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW).strip()
            for line in gpu_out.splitlines():
                if line.strip():
                    specs.append(f"  • GPU:         {line.strip()}")
        except Exception:
            specs.append("  • GPU:         Не удалось опросить WMI")

        try:
            user32 = ctypes.windll.user32
            screens = user32.GetSystemMetrics(80)  # SM_CMONITORS
            virt_w = user32.GetSystemMetrics(78)   # SM_CXVIRTUALSCREEN
            virt_h = user32.GetSystemMetrics(79)   # SM_CYVIRTUALSCREEN
            specs.append(f"  • Мониторов:   {screens} шт. | Виртуальный холст: {virt_w}x{virt_h} px")
        except Exception:
            pass

        final_text = "\n".join(specs)
        if self.win.winfo_exists():
            self.win.after(0, self._update_textbox, final_text)

    def _update_textbox(self, text: str):
        if self.win.winfo_exists():
            self.text_box.delete("1.0", tk.END)
            self.text_box.insert(tk.END, text)


class SentinelOSApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME)

        self.root.state("zoomed")
        self.root.minsize(1020, 680)
        self.root.configure(bg="#060b13")

        self.is_running = True
        self.check_interval_seconds = 60
        self.recent_retention_seconds = 90 * 60
        self.countdown = self.check_interval_seconds
        self.total_sorted_counter = 0
        self.cycle_lock = threading.Lock()

        # История команд терминала
        self.cmd_history = []
        self.history_idx = -1

        # Метаданные времени попадания файлов в «Недавнее»
        self.recent_timestamps = {}

        self.tray_icon = None
        self.pystray_ready = False
        self.ico_path = ""

        self.pulse_step = 0
        self.is_busy = False
        self.busy_pos = 0

        self._load_config()
        self._init_theme()
        self._build_gradient_background()
        self._build_ui()

        self._animate_pulse()
        self._update_live_telemetry()

        threading.Thread(target=self._bootstrap_environment, daemon=True).start()

    # ── КОНФИГУРАЦИЯ ──────────────────────────────────────────────────────
    def _load_config(self):
        if CONFIG_FILE.exists():
            try:
                data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
                self.check_interval_seconds = data.get("interval", 60)
                self.recent_retention_seconds = data.get("retention", 90 * 60)
                self.total_sorted_counter = data.get("sorted_total", 0)
                self.countdown = self.check_interval_seconds
            except Exception:
                pass

    def _save_config(self):
        try:
            data = {
                "interval": self.check_interval_seconds,
                "retention": self.recent_retention_seconds,
                "sorted_total": self.total_sorted_counter
            }
            CONFIG_FILE.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    # ── ТЕМА И UI ─────────────────────────────────────────────────────────
    def _init_theme(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure(
            "Dark.TCombobox",
            fieldbackground="#111c2d",
            background="#0b1420",
            foreground="#38bdf8",
            darkcolor="#111c2d",
            lightcolor="#111c2d",
            selectbackground="#111c2d",
            selectforeground="#38bdf8",
            arrowcolor="#38bdf8",
            bordercolor="#1e344f"
        )
        style.map(
            "Dark.TCombobox",
            fieldbackground=[("readonly", "#111c2d"), ("focus", "#111c2d")],
            selectbackground=[("readonly", "#111c2d")],
            selectforeground=[("readonly", "#38bdf8")],
            foreground=[("readonly", "#38bdf8")]
        )

        self.root.option_add("*TCombobox*Listbox.background", "#0b1420")
        self.root.option_add("*TCombobox*Listbox.foreground", "#38bdf8")
        self.root.option_add("*TCombobox*Listbox.selectBackground", "#0284c7")
        self.root.option_add("*TCombobox*Listbox.selectForeground", "#ffffff")
        self.root.option_add("*TCombobox*Listbox.relief", "flat")

    def _build_gradient_background(self):
        self.bg_canvas = tk.Canvas(self.root, highlightthickness=0)
        self.bg_canvas.place(x=0, y=0, relwidth=1, relheight=1)
        self.root.bind("<Configure>", self._draw_gradient)

    def _draw_gradient(self, event=None):
        if event and event.widget != self.root:
            return
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        if width <= 1 or height <= 1:
            return

        self.bg_canvas.delete("grad")
        steps = 36
        c1 = (5, 9, 16)
        c2 = (14, 25, 42)

        for i in range(steps):
            r = int(c1[0] + (c2[0] - c1[0]) * (i / steps))
            g = int(c1[1] + (c2[1] - c1[1]) * (i / steps))
            b = int(c1[2] + (c2[2] - c1[2]) * (i / steps))
            color = f"#{r:02x}{g:02x}{b:02x}"
            y1 = int(i * (height / steps))
            y2 = int((i + 1) * (height / steps))
            self.bg_canvas.create_rectangle(0, y1, width, y2, fill=color, outline="", tags="grad")
        self.bg_canvas.tag_lower("grad")

    def _create_hover_btn(self, parent, text, bg, fg, hover_bg, cmd, padx=12, pady=6):
        btn = tk.Button(
            parent,
            text=text,
            bg=bg,
            fg=fg,
            activebackground=hover_bg,
            activeforeground=fg,
            relief="flat",
            bd=0,
            padx=padx,
            pady=pady,
            font=("Segoe UI", 9, "bold"),
            cursor="hand2",
            command=cmd
        )
        btn.default_bg = bg
        btn.hover_bg = hover_bg
        btn.bind("<Enter>", lambda e: btn.config(bg=btn.hover_bg))
        btn.bind("<Leave>", lambda e: btn.config(bg=btn.default_bg))
        return btn

    def _build_ui(self):
        content = tk.Frame(self.root, bg="#060b13")
        content.pack(fill=tk.BOTH, expand=True, padx=14, pady=10)

        # 1. ВЕРХНИЙ ДАШБОРД И ЖИВАЯ ТЕЛЕМЕТРИЯ
        header = tk.Frame(content, bg="#0b1522", padx=18, pady=10, highlightthickness=1, highlightbackground="#1e344f")
        header.pack(fill=tk.X, pady=(0, 6))

        self.lbl_status = tk.Label(
            header,
            text="● SENTINEL ACTIVE",
            fg="#10b981",
            bg="#0b1522",
            font=("Consolas", 13, "bold")
        )
        self.lbl_status.pack(side=tk.LEFT)

        self.lbl_stats = tk.Label(
            header,
            text=f"Сортировано: {self.total_sorted_counter}",
            fg="#e2e8f0",
            bg="#0b1522",
            font=("Segoe UI", 10, "bold")
        )
        self.lbl_stats.pack(side=tk.LEFT, padx=(24, 16))

        # Живые датчики CPU / RAM в шапке
        telemetry_box = tk.Frame(header, bg="#070e17", padx=10, pady=4, highlightthickness=1, highlightbackground="#162a40")
        telemetry_box.pack(side=tk.LEFT, padx=10)

        self.lbl_cpu_live = tk.Label(telemetry_box, text="CPU: --%", fg="#38bdf8", bg="#070e17", font=("Consolas", 9, "bold"))
        self.lbl_cpu_live.pack(side=tk.LEFT, padx=(0, 12))

        self.lbl_ram_live = tk.Label(telemetry_box, text="RAM: --%", fg="#a78bfa", bg="#070e17", font=("Consolas", 9, "bold"))
        self.lbl_ram_live.pack(side=tk.LEFT)

        self.lbl_timer = tk.Label(
            header,
            text=f"Цикл через: {self.countdown} с",
            fg="#38bdf8",
            bg="#0b1522",
            font=("Consolas", 11, "bold")
        )
        self.lbl_timer.pack(side=tk.RIGHT)

        # 2. ПАНЕЛЬ ПАРАМЕТРОВ ВРЕМЕНИ И АВТОЗАПУСКА
        cfg_panel = tk.Frame(content, bg="#09111b", padx=16, pady=8, highlightthickness=1, highlightbackground="#172a40")
        cfg_panel.pack(fill=tk.X, pady=3)

        tk.Label(cfg_panel, text="⏱ Интервал:", bg="#09111b", fg="#94a3b8", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(0, 6))

        inv_map = {30: "30 сек", 60: "60 сек", 120: "2 мин", 300: "5 мин"}
        self.interval_var = tk.StringVar(value=inv_map.get(self.check_interval_seconds, "60 сек"))
        self.interval_combo = ttk.Combobox(
            cfg_panel,
            textvariable=self.interval_var,
            values=["30 сек", "60 сек", "2 мин", "5 мин"],
            state="readonly",
            style="Dark.TCombobox",
            width=9,
            font=("Segoe UI", 9)
        )
        self.interval_combo.pack(side=tk.LEFT, padx=(0, 20))
        self.interval_combo.bind("<<ComboboxSelected>>", self._on_interval_change)

        tk.Label(cfg_panel, text="⏳ Буфер «Недавнее»:", bg="#09111b", fg="#94a3b8", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(0, 6))

        ret_map = {0: "Без буфера (сразу)", 900: "15 мин", 1800: "30 мин", 3600: "1 час", 5400: "1.5 часа", 10800: "3 часа"}
        self.retention_var = tk.StringVar(value=ret_map.get(self.recent_retention_seconds, "1.5 часа"))
        self.retention_combo = ttk.Combobox(
            cfg_panel,
            textvariable=self.retention_var,
            values=["Без буфера (сразу)", "15 мин", "30 мин", "1 час", "1.5 часа", "3 часа"],
            state="readonly",
            style="Dark.TCombobox",
            width=18,
            font=("Segoe UI", 9)
        )
        self.retention_combo.pack(side=tk.LEFT)
        self.retention_combo.bind("<<ComboboxSelected>>", self._on_retention_change)

        is_auto = self._is_autostart_enabled()
        self.btn_autostart = self._create_hover_btn(
            cfg_panel,
            text=self._get_autostart_label(),
            bg="#065f46" if is_auto else "#131e2e",
            fg="#34d399" if is_auto else "#38bdf8",
            hover_bg="#047857" if is_auto else "#1d2e46",
            cmd=self._toggle_autostart,
            padx=12,
            pady=4
        )
        self.btn_autostart.pack(side=tk.RIGHT)

        # 3. ПАНЕЛЬ ОПЕРАТИВНОГО УПРАВЛЕНИЯ (2 РЯДА)
        row1_panel = tk.Frame(content, bg="#060b13")
        row1_panel.pack(fill=tk.X, pady=4)

        self._create_hover_btn(row1_panel, "⚡ Сортировать сейчас", "#0284c7", "#ffffff", "#0369a1", self._manual_run).pack(side=tk.LEFT, padx=(0, 4))
        self._create_hover_btn(row1_panel, "🔨 Внутри папок", "#2563eb", "#ffffff", "#1d4ed8", self._manual_subsort).pack(side=tk.LEFT, padx=4)
        self._create_hover_btn(row1_panel, "🎯 Дубликаты (Smart MD5)", "#334155", "#f8fafc", "#475569", lambda: threading.Thread(target=self._find_and_delete_duplicates, daemon=True).start()).pack(side=tk.LEFT, padx=4)
        self._create_hover_btn(row1_panel, "🛡 Аудит Защиты", "#dc2626", "#ffffff", "#b91c1c", lambda: threading.Thread(target=self._deep_system_security_scan, daemon=True).start()).pack(side=tk.LEFT, padx=4)
        self._create_hover_btn(row1_panel, "🔍 Телеметрия ПК", "#475569", "#ffffff", "#64748b", lambda: HardwareDiagWindow(self.root)).pack(side=tk.LEFT, padx=4)

        self._create_hover_btn(row1_panel, "📥 Скрыть в трей", "#059669", "#ffffff", "#047857", self.hide_to_tray).pack(side=tk.RIGHT, padx=(4, 0))
        self.btn_toggle = self._create_hover_btn(row1_panel, "⏸ Пауза", "#1e293b", "#f1f5f9", "#334155", self._toggle_monitoring)
        self.btn_toggle.pack(side=tk.RIGHT, padx=4)

        row2_panel = tk.Frame(content, bg="#060b13")
        row2_panel.pack(fill=tk.X, pady=2)

        self._create_hover_btn(row2_panel, "🧹 Очистить Temp", "#1e293b", "#cbd5e1", "#334155", lambda: threading.Thread(target=self._clean_temp_files, daemon=True).start(), padx=10, pady=4).pack(side=tk.LEFT, padx=(0, 4))
        self._create_hover_btn(row2_panel, "⚡ Сброс видеодрайвера (GPU)", "#7c2d12", "#fed7aa", "#9a3412", self._restart_graphics_driver, padx=10, pady=4).pack(side=tk.LEFT, padx=4)
        self._create_hover_btn(row2_panel, "☀️ Зона Релакса", "#eab308", "#090d16", "#ca8a04", lambda: NatureRelaxWindow(self.root), padx=10, pady=4).pack(side=tk.LEFT, padx=4)
        self._create_hover_btn(row2_panel, "🗑 Очистить лог", "#111827", "#64748b", "#1f2937", lambda: self.log_text.delete("1.0", tk.END), padx=10, pady=4).pack(side=tk.LEFT, padx=4)

        self._create_hover_btn(row2_panel, "📂 Открыть Загрузки", "#0f172a", "#38bdf8", "#1e293b", lambda: self._open_dir(TARGET_DIR), padx=10, pady=4).pack(side=tk.RIGHT, padx=(4, 0))
        self._create_hover_btn(row2_panel, "📁 Буфер «Недавнее»", "#0f172a", "#94a3b8", "#1e293b", lambda: self._open_dir(TARGET_DIR / RECENT_FOLDER_NAME), padx=10, pady=4).pack(side=tk.RIGHT, padx=4)

        # 4. ЦВЕТОВОЙ ТЕРМИНАЛ SENTINEL
        terminal_frame = tk.Frame(content, bg="#030609", highlightthickness=1, highlightbackground="#153226")
        terminal_frame.pack(fill=tk.BOTH, expand=True, pady=(6, 2))

        self.log_text = tk.Text(
            terminal_frame,
            bg="#030609",
            fg="#34d399",
            insertbackground="#34d399",
            selectbackground="#065f46",
            font=("Consolas", 11),
            relief="flat",
            padx=14,
            pady=12
        )
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Цветовые теги для логов
        self.log_text.tag_config("TIME", foreground="#475569")
        self.log_text.tag_config("INFO", foreground="#34d399")
        self.log_text.tag_config("SYS", foreground="#38bdf8")
        self.log_text.tag_config("WARN", foreground="#facc15")
        self.log_text.tag_config("ERR", foreground="#f87171")
        self.log_text.tag_config("SECRET", foreground="#c084fc", font=("Consolas", 11, "bold"))

        scrollbar = tk.Scrollbar(terminal_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar.set)

        # Неоновая полоса активности
        self.scan_bar_canvas = tk.Canvas(content, height=4, bg="#060b13", highlightthickness=0)
        self.scan_bar_canvas.pack(fill=tk.X, pady=(2, 3))

        # 5. КОМАНДНАЯ СТРОКА С ИСТОРИЕЙ И АВТОДОПОЛНЕНИЕМ
        cmd_input_frame = tk.Frame(content, bg="#06120d", highlightthickness=1, highlightbackground="#1a4930")
        cmd_input_frame.pack(fill=tk.X, pady=(0, 2))

        lbl_prompt = tk.Label(
            cmd_input_frame,
            text="Operator@Sentinel:~$ ",
            fg="#4ade80",
            bg="#06120d",
            font=("Consolas", 11, "bold")
        )
        lbl_prompt.pack(side=tk.LEFT, padx=(10, 0), pady=7)

        self.cmd_entry = tk.Entry(
            cmd_input_frame,
            bg="#06120d",
            fg="#a7f3d0",
            insertbackground="#4ade80",
            relief="flat",
            font=("Consolas", 11)
        )
        self.cmd_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8, pady=7)
        self.cmd_entry.bind("<Return>", self._handle_terminal_cmd)
        self.cmd_entry.bind("<Up>", self._history_up)
        self.cmd_entry.bind("<Down>", self._history_down)
        self.cmd_entry.bind("<Tab>", self._autocomplete_cmd)

        self.root.protocol("WM_DELETE_WINDOW", self.hide_to_tray)

    # ── ПОТОКОБЕЗОПАСНОЕ ЛОГИРОВАНИЕ И АНИМАЦИИ ───────────────────────────
    def log(self, message: str, level: str = "AUTO"):
        """Потокобезопасный вывод в консоль с автоматической раскраской."""
        self.root.after(0, self._log_Safe, message, level)

    def _log_Safe(self, message: str, level: str):
        now = datetime.now().strftime("%H:%M:%S")
        if level == "AUTO":
            if any(k in message for k in ("[x]", "[Err]", "Ошибка", "ТРЕВОГА", "[!]")):
                level = "ERR" if "[x]" in message or "Ошибка" in message else "WARN"
            elif any(k in message for k in (">>", "[Автоцикл]", "Интервал", "Буфер")):
                level = "SYS"
            elif "★" in message:
                level = "SECRET"
            else:
                level = "INFO"

        self.log_text.insert(tk.END, f"[{now}] ", "TIME")
        self.log_text.insert(tk.END, f"{message}\n", level)
        self.log_text.see(tk.END)

    def _animate_pulse(self):
        if self.is_running:
            self.pulse_step = (self.pulse_step + 1) % 10
            pulse_colors = [
                "#10b981", "#22c55e", "#4ade80", "#86efac", "#4ade80",
                "#22c55e", "#10b981", "#059669", "#047857", "#059669"
            ]
            self.lbl_status.config(fg=pulse_colors[self.pulse_step])
        self.root.after(140, self._animate_pulse)

    def _update_live_telemetry(self):
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory().percent
            cpu_color = "#f87171" if cpu > 80 else ("#facc15" if cpu > 50 else "#38bdf8")
            ram_color = "#f87171" if ram > 85 else "#a78bfa"
            self.lbl_cpu_live.config(text=f"CPU: {cpu:4.1f}%", fg=cpu_color)
            self.lbl_ram_live.config(text=f"RAM: {ram:4.1f}%", fg=ram_color)
        except Exception:
            pass
        self.root.after(2000, self._update_live_telemetry)

    def _animate_busy_bar(self):
        if self.is_busy:
            w = max(self.scan_bar_canvas.winfo_width(), 300)
            self.busy_pos = (self.busy_pos + 22) % (w + 160)
            self.scan_bar_canvas.delete("wave")
            self.scan_bar_canvas.create_rectangle(
                self.busy_pos - 140, 0, self.busy_pos, 4,
                fill="#38bdf8", outline="", tags="wave"
            )
            self.root.after(25, self._animate_busy_bar)
        else:
            self.scan_bar_canvas.delete("wave")

    def _set_busy(self, status: bool):
        def _apply():
            was_busy = self.is_busy
            self.is_busy = status
            if status and not was_busy:
                self._animate_busy_bar()
            elif not status:
                self.scan_bar_canvas.delete("wave")
        self.root.after(0, _apply)

    # ── СИСТЕМНЫЕ ИНСТРУМЕНТЫ И ЗАЩИТА ────────────────────────────────────
    def _deep_system_security_scan(self):
        self._set_busy(True)
        self.log(">> [SENTINEL-AV] Старт углубленного аудита безопасности...", "SYS")
        threats_found = []

        # 1. Hosts
        self.log(">> [1/4] Проверка системного маршрутизатора (hosts)...", "SYS")
        hosts_path = Path(r"C:\Windows\System32\drivers\etc\hosts")
        if hosts_path.exists():
            try:
                hosts_text = hosts_path.read_text(encoding="utf-8", errors="ignore").lower()
                for blocked in ["kaspersky", "drweb", "malwarebytes", "virustotal", "avast", "windowsupdate"]:
                    if blocked in hosts_text and ("127.0.0.1" in hosts_text or "0.0.0.0" in hosts_text):
                        threats_found.append((hosts_path, f"Блокировка домена безопасности ({blocked}) в файле hosts"))
            except Exception:
                pass

        # 2. Реестр автозагрузки
        self.log(">> [2/4] Анализ ключей автозагрузки реестра Windows...", "SYS")
        reg_keys = [
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run"),
            (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run"),
        ]
        for root_k, sub_k in reg_keys:
            try:
                with winreg.OpenKey(root_k, sub_k, 0, winreg.KEY_READ) as k:
                    for i in range(winreg.QueryInfoKey(k)[1]):
                        name, val, _ = winreg.EnumValue(k, i)
                        v_lower = str(val).lower()
                        if any(s in v_lower for s in ("appdata\\local\\temp", "powershell", "wscript", "cscript", "mshta")):
                            self.log(f"  [!] Подозрительный автозапуск: {name} -> {val}", "WARN")
                            threats_found.append((Path(str(val)), f"Подозрительный ключ реестра: {name}"))
            except Exception:
                pass

        # 3. Процессы в ОЗУ
        self.log(">> [3/4] Сканирование активных процессов в памяти...", "SYS")
        try:
            import psutil
            for proc in psutil.process_iter(['pid', 'name', 'exe']):
                try:
                    exe = (proc.info['exe'] or "").lower()
                    if exe and ("appdata\\local\\temp" in exe) and "python" not in exe:
                        if exe.endswith((".exe", ".vbs", ".bat", ".cmd", ".scr")):
                            self.log(f"  [!] Процесс из Temp: PID {proc.info['pid']} ({proc.info['name']})", "WARN")
                            threats_found.append((Path(exe), f"Активный процесс из папки Temp [PID {proc.info['pid']}]"))
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception:
            pass

        # 4. Файловая сигнатурная проверка
        self.log(">> [4/4] Сигнатурный анализ загрузок и автозагрузки...", "SYS")
        startup_dir = Path(os.environ.get("APPDATA", "")) / r"Microsoft\Windows\Start Menu\Programs\Startup"
        scan_targets = [TARGET_DIR, startup_dir]
        fake_ext_pattern = [".pdf.exe", ".jpg.exe", ".png.exe", ".docx.exe", ".xlsx.exe", ".txt.vbs", ".doc.scr", ".mp3.exe"]
        quarantine_dir = (TARGET_DIR / QUARANTINE_FOLDER_NAME).resolve()

        scanned_files = 0
        for s_dir in scan_targets:
            if not s_dir.exists():
                continue
            for file_path in s_dir.rglob("*"):
                try:
                    if quarantine_dir in file_path.resolve().parents:
                        continue
                    if not file_path.is_file() or file_path.suffix.lower() in TEMP_EXTENSIONS:
                        continue
                except Exception:
                    continue

                scanned_files += 1
                if scanned_files % 200 == 0:
                    self.log(f"  Проверено файлов: {scanned_files}...", "SYS")

                fname_lower = file_path.name.lower()
                for bad_combo in fake_ext_pattern:
                    if fname_lower.endswith(bad_combo):
                        threats_found.append((file_path, f"Маскировка двойного расширения ({bad_combo})"))
                        break

                if "\u202e" in file_path.name:
                    threats_found.append((file_path, "Скрытый юникод-символ подмены расширения (RTLO)"))

                if file_path.suffix.lower() in [".bat", ".cmd", ".ps1", ".vbs", ".js"]:
                    try:
                        with open(file_path, "rb") as f:
                            content = f.read(256 * 1024).lower()
                            for pattern in MALICIOUS_PATTERNS:
                                if pattern in content:
                                    pat_str = pattern.decode('latin1', errors='ignore')
                                    threats_found.append((file_path, f"Опасный пейлоад: {pat_str}"))
                                    break
                    except Exception:
                        pass

        self._set_busy(False)
        self.log(f">> Аудит завершен. Проверено объектов: {scanned_files}", "SYS")

        if not threats_found:
            self.log("✓ [SENTINEL-AV] Угроз не обнаружено. Память, реестр и файлы чисты.", "INFO")
            return

        self.log(f"⚠️ [ТРЕВОГА] Найдено подозрительных объектов: {len(threats_found)}", "ERR")
        for path, reason in threats_found:
            self.log(f"  [!] {path.name} -> {reason}", "WARN")

        # Вызов диалогового окна строго в главном потоке Tkinter!
        self.root.after(0, self._prompt_quarantine, threats_found)

    def _prompt_quarantine(self, threats_found):
        res = messagebox.askyesno(
            "Sentinel OS — Защитник Системы",
            f"Обнаружено подозрительных объектов: {len(threats_found)} шт.\n\n"
            "Переместить подозрительные файлы в изолированный карантин (Quarantine)?"
        )
        if res:
            q_dir = TARGET_DIR / QUARANTINE_FOLDER_NAME
            q_dir.mkdir(exist_ok=True)
            for path, _ in threats_found:
                try:
                    if path.exists() and path.is_file() and path.name.lower() != "hosts":
                        dest = self._resolve_unique_path(q_dir, path.name + ".quarantined")
                        shutil.move(str(path), str(dest))
                        self.log(f"🔒 Изолирован в карантин: {path.name}", "INFO")
                except Exception as e:
                    self.log(f"[x] Не удалось изолировать {path.name}: {e}", "ERR")

    def _find_and_delete_duplicates(self):
        """Умный двухэтапный поиск дубликатов: сначала по размеру, затем по MD5."""
        self._set_busy(True)
        self.log(">> [SMART-MD5] Поиск дубликатов (группировка по размеру + хеширование)...", "SYS")

        size_groups = {}
        quarantine_dir = (TARGET_DIR / QUARANTINE_FOLDER_NAME).resolve()

        for file_path in list(TARGET_DIR.rglob("*")):
            try:
                if not file_path.is_file():
                    continue
                if quarantine_dir in file_path.resolve().parents:
                    continue
                if file_path.suffix.lower() in TEMP_EXTENSIONS or file_path.name.lower() in IGNORED_FILES:
                    continue
                f_size = file_path.stat().st_size
                if f_size == 0:
                    continue
                size_groups.setdefault(f_size, []).append(file_path)
            except Exception:
                continue

        def get_file_md5(p: Path):
            hasher = hashlib.md5()
            with open(p, "rb") as f:
                for chunk in iter(lambda: f.read(131072), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()

        duplicates_removed = 0
        freed_bytes = 0

        # Считаем MD5 только там, где есть 2+ файла одинакового размера
        for f_size, files in size_groups.items():
            if len(files) < 2:
                continue
            hashes = {}
            for file_path in files:
                try:
                    f_hash = get_file_md5(file_path)
                    if f_hash in hashes:
                        orig = hashes[f_hash]
                        file_path.unlink()
                        duplicates_removed += 1
                        freed_bytes += f_size
                        self.log(f"[Удалён дубликат] «{file_path.name}» == «{orig.name}»", "INFO")
                    else:
                        hashes[f_hash] = file_path
                except Exception as e:
                    self.log(f"[Err] {file_path.name}: {e}", "ERR")

        self._set_busy(False)
        if duplicates_removed == 0:
            self.log("✓ Проверка завершена: дубликатов не обнаружено.", "INFO")
        else:
            freed_mb = round(freed_bytes / (1024 * 1024), 2)
            self.log(f"★ Удалено дубликатов: {duplicates_removed} шт. | Освобождено: {freed_mb} MB", "SECRET")

    def _clean_temp_files(self):
        self._set_busy(True)
        temp_dir = Path(tempfile.gettempdir())
        self.log(f">> Очистка временного кэша системы: {temp_dir}", "SYS")
        deleted_count = 0
        freed_bytes = 0

        for item in list(temp_dir.iterdir()):
            if "sentinel" in item.name.lower():
                continue
            try:
                if item.is_file():
                    size = item.stat().st_size
                    item.unlink()
                    deleted_count += 1
                    freed_bytes += size
                elif item.is_dir():
                    shutil.rmtree(item, ignore_errors=True)
                    deleted_count += 1
            except Exception:
                continue

        self._set_busy(False)
        freed_mb = round(freed_bytes / (1024 * 1024), 2)
        self.log(f"✓ Temp очищен! Удалено объектов: {deleted_count} | Освобождено: {freed_mb} MB", "INFO")

    def _restart_graphics_driver(self):
        """Реальный горячий сброс видеодрайвера Windows через эмуляцию Win+Ctrl+Shift+B."""
        self.log(">> Отправка аппаратного сигнала сброса видеодрайвера (Win+Ctrl+Shift+B)...", "SYS")
        try:
            user32 = ctypes.windll.user32
            VK_LWIN = 0x5B
            VK_CONTROL = 0x11
            VK_SHIFT = 0x10
            VK_B = 0x42
            KEYEVENTF_KEYUP = 0x0002

            # Зажимаем комбинацию
            user32.keybd_event(VK_LWIN, 0, 0, 0)
            user32.keybd_event(VK_CONTROL, 0, 0, 0)
            user32.keybd_event(VK_SHIFT, 0, 0, 0)
            user32.keybd_event(VK_B, 0, 0, 0)
            time.sleep(0.05)
            # Отпускаем
            user32.keybd_event(VK_B, 0, KEYEVENTF_KEYUP, 0)
            user32.keybd_event(VK_SHIFT, 0, KEYEVENTF_KEYUP, 0)
            user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)
            user32.keybd_event(VK_LWIN, 0, KEYEVENTF_KEYUP, 0)

            self.log("✓ Сигнал Win+Ctrl+Shift+B выполнен. Видеоподсистема и экраны перезагружены.", "INFO")
        except Exception as e:
            self.log(f"[x] Ошибка сброса видеодрайвера: {e}", "ERR")

    # ── ИНИЦИАЛИЗАЦИЯ И ТРЕЙ ──────────────────────────────────────────────
    def _bootstrap_environment(self):
        self.log(f">> Инициализация ядра {APP_NAME}...", "SYS")

        self.ico_path = generate_app_icon_file()
        if self.ico_path and os.path.exists(self.ico_path):
            self.root.after(0, lambda: self.root.iconbitmap(self.ico_path))

        required = {"pystray": "pystray", "PIL": "pillow", "psutil": "psutil"}
        missing = []

        for mod, pip_name in required.items():
            try:
                __import__(mod)
            except ImportError:
                missing.append(pip_name)

        if missing:
            self.log(f"(!) Доустановка модулей: {', '.join(missing)}", "WARN")
            py_bin = get_console_python_path()
            for pkg in missing:
                self.log(f">> Загрузка пакета {pkg}...", "SYS")
                cmd = [py_bin, "-m", "pip", "install", pkg]
                try:
                    proc = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                    for line in proc.stdout:
                        if line.strip():
                            self.log(f"  pip: {line.strip()}", "SYS")
                    proc.wait()
                    if proc.returncode == 0:
                        self.log(f"✓ Модуль {pkg} успешно интегрирован!", "INFO")
                except Exception as e:
                    self.log(f"[x] Ошибка установки {pkg}: {e}", "ERR")

        self._init_tray_safe()
        self.log(">> Все системы в норме, Operator. Введите 'help' для списка команд.", "INFO")

        threading.Thread(target=self._deep_subsort, daemon=True).start()
        threading.Thread(target=self._execute_cycle, daemon=True).start()
        self.root.after(1000, self._tick_timer)

    def _init_tray_safe(self):
        try:
            import pystray
            from PIL import Image

            if self.ico_path and os.path.exists(self.ico_path):
                img = Image.open(self.ico_path)
            else:
                img = Image.new("RGBA", (64, 64), color=(16, 185, 129))

            menu = pystray.Menu(
                pystray.MenuItem("Развернуть Sentinel OS", self.show_from_tray, default=True),
                pystray.MenuItem("Сортировать сейчас", lambda: self._manual_run()),
                pystray.MenuItem("Сброс GPU", lambda: self._restart_graphics_driver()),
                pystray.MenuItem("Выход", self._quit_app)
            )
            self.tray_icon = pystray.Icon(APP_NAME, img, APP_NAME, menu)
            threading.Thread(target=self.tray_icon.run, daemon=True).start()
            self.pystray_ready = True
        except Exception:
            pass

    def hide_to_tray(self):
        if self.pystray_ready:
            self.root.withdraw()
        else:
            self.root.iconify()

    def show_from_tray(self, icon=None, item=None):
        self.root.after(0, self.root.deiconify)
        self.root.after(0, lambda: self.root.state("zoomed"))
        self.root.after(0, self.root.lift)

    def _quit_app(self, icon=None, item=None):
        self._save_config()
        if self.tray_icon:
            self.tray_icon.stop()
        self.root.after(0, self.root.destroy)

    def _open_dir(self, path: Path):
        path.mkdir(parents=True, exist_ok=True)
        os.startfile(path)

    # ── АВТОЗАГРУЗКА WINDOWS ──────────────────────────────────────────────
    def _is_autostart_enabled(self) -> bool:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTORUN_REG_KEY, 0, winreg.KEY_READ) as key:
                val, _ = winreg.QueryValueEx(key, "Sentinel OS")
                return bool(val)
        except FileNotFoundError:
            return False

    def _get_autostart_label(self) -> str:
        return "🚀 Автозапуск: [ВКЛ]" if self._is_autostart_enabled() else "🚀 Автозапуск: [ВЫКЛ]"

    def _toggle_autostart(self):
        is_on = self._is_autostart_enabled()
        script_path = os.path.abspath(sys.argv[0])

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTORUN_REG_KEY, 0, winreg.KEY_WRITE) as key:
            if is_on:
                try:
                    winreg.DeleteValue(key, "Sentinel OS")
                except FileNotFoundError:
                    pass
                self.log("Автозагрузка при старте Windows отключена.", "WARN")
            else:
                pythonw_exe = Path(sys.executable).parent / "pythonw.exe"
                exec_bin = pythonw_exe if pythonw_exe.exists() else Path(sys.executable)
                cmd = f'"{exec_bin}" "{script_path}"'
                winreg.SetValueEx(key, "Sentinel OS", 0, winreg.REG_SZ, cmd)
                self.log("Sentinel OS добавлен в автозагрузку Windows.", "INFO")

        is_now_on = self._is_autostart_enabled()
        bg = "#065f46" if is_now_on else "#131e2e"
        fg = "#34d399" if is_now_on else "#38bdf8"
        hover = "#047857" if is_now_on else "#1d2e46"
        self.btn_autostart.default_bg = bg
        self.btn_autostart.hover_bg = hover
        self.btn_autostart.config(text=self._get_autostart_label(), bg=bg, fg=fg)

    # ── ТЕРМИНАЛ И КОМАНДЫ ────────────────────────────────────────────────
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

    def _autocomplete_cmd(self, event):
        commands = [
            "help", "sort", "scan", "antivirus", "relax", "clean", "dups",
            "specs", "cls", "open", "gpu", "matrix", "operator", "rats", "bioshock"
        ]
        cur = self.cmd_entry.get().strip().lower()
        if cur:
            matches = [c for c in commands if c.startswith(cur)]
            if len(matches) == 1:
                self.cmd_entry.delete(0, tk.END)
                self.cmd_entry.insert(0, matches[0])
        return "break"

    def _handle_terminal_cmd(self, event=None):
        raw_cmd = self.cmd_entry.get().strip()
        self.cmd_entry.delete(0, tk.END)
        if not raw_cmd:
            return

        self.cmd_history.append(raw_cmd)
        self.history_idx = len(self.cmd_history)

        self.log(f"Operator@Sentinel:~$ {raw_cmd}", "SYS")
        root_cmd = raw_cmd.split()[0].lower()

        if root_cmd in ("operator", "opetator", "оператор", "vladosic", "vladosic15"):
            self.log("★ [ПРОТОКОЛ ДОСТУПА] Приветствую, Operator. Все три монитора, ядра и диски под защитой.", "SECRET")
        elif root_cmd in ("bio", "rapture", "bioshock"):
            self.log("★ [RAPTURE] «Would you kindly...» — Системы Восторга функционируют стабильно.", "SECRET")
        elif root_cmd in ("rats", "cheese", "крысы", "принц", "толик"):
            self.log("★ Принц и Толик провели ревизию проводов и одобрили порядок в системе! 🐀🐀", "SECRET")
        elif root_cmd in ("fl", "music", "музыка"):
            self.log("★ [STUDIO] Профиль сортировки .flp / .vst3 / .wav активен. Вдохновения в треках!", "SECRET")
        elif root_cmd == "matrix":
            self._easter_egg_matrix()
        elif root_cmd in ("relax", "солнце", "полянка"):
            NatureRelaxWindow(self.root)
        elif root_cmd in ("scan-av", "antivirus", "защита"):
            threading.Thread(target=self._deep_system_security_scan, daemon=True).start()
        elif root_cmd == "gpu":
            self._restart_graphics_driver()
        elif root_cmd in ("help", "?"):
            self.log("╔══ СПИСОК КОМАНД SENTINEL OS v5.0 ══════════════════════════╗", "SYS")
            self.log("  scan      - мгновенно проверить папку Загрузки", "INFO")
            self.log("  sort      - глубокая сортировка файлов внутри категорий", "INFO")
            self.log("  dups      - быстрый поиск и удаление дубликатов (Smart MD5)", "INFO")
            self.log("  antivirus - глубокий аудит памяти, реестра, hosts и скриптов", "INFO")
            self.log("  clean     - очистить системный кэш Temp", "INFO")
            self.log("  gpu       - горячий перезапуск видеодрайвера (Win+Ctrl+Shift+B)", "INFO")
            self.log("  specs     - открыть окно аппаратной телеметрии ПК", "INFO")
            self.log("  relax     - открыть анимированную зону отдыха", "INFO")
            self.log("  open      - открыть папку Загрузки в Проводнике", "INFO")
            self.log("  cls       - очистить окно терминала", "INFO")
            self.log("  <команда> - выполнить любую системную команду Windows CMD", "INFO")
            self.log("  [Подсказка: используй ↑/↓ для истории команд и Tab для автодополнения]", "SYS")
        elif root_cmd == "cls":
            self.log_text.delete("1.0", tk.END)
        elif root_cmd == "sort":
            threading.Thread(target=self._deep_subsort, daemon=True).start()
        elif root_cmd == "scan":
            self._manual_run()
        elif root_cmd == "clean":
            threading.Thread(target=self._clean_temp_files, daemon=True).start()
        elif root_cmd == "dups":
            threading.Thread(target=self._find_and_delete_duplicates, daemon=True).start()
        elif root_cmd in ("specs", "diag"):
            HardwareDiagWindow(self.root)
        elif root_cmd == "open":
            self._open_dir(TARGET_DIR)
        else:
            threading.Thread(target=self._run_system_cmd, args=(raw_cmd,), daemon=True).start()

    def _easter_egg_matrix(self):
        def stream():
            import random
            chars = "01010101XYZABCDEF@#$%&*+=-"
            for _ in range(14):
                line = "".join(random.choice(chars) for _ in range(60))
                self.log(f"  {line}", "INFO")
                time.sleep(0.04)
            self.log("★ Matrix sub-routine complete. Follow the white rabbit, Operator.", "SECRET")
        threading.Thread(target=stream, daemon=True).start()

    def _run_system_cmd(self, cmd: str):
        try:
            res = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                encoding="cp866",
                errors="replace",
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            output = res.stdout if res.stdout else res.stderr
            for line in output.splitlines():
                if line.strip():
                    self.log(f"  {line}", "INFO")
        except Exception as e:
            self.log(f"[x] Ошибка выполнения команды: {e}", "ERR")

    # ── ТАЙМИНГИ И ЕДИНЫЙ ТАКТОВЫЙ ГЕНЕРАТОР ──────────────────────────────
    def _on_interval_change(self, event=None):
        mapping = {"30 сек": 30, "60 сек": 60, "2 мин": 120, "5 мин": 300}
        self.check_interval_seconds = mapping.get(self.interval_var.get(), 60)
        self.countdown = self.check_interval_seconds
        self.lbl_timer.config(text=f"Цикл через: {self.countdown} с")
        self._save_config()
        self.log(f"Интервал автосканирования изменен на: {self.interval_var.get()}", "SYS")

    def _on_retention_change(self, event=None):
        mapping = {
            "Без буфера (сразу)": 0,
            "15 мин": 15 * 60,
            "30 мин": 30 * 60,
            "1 час": 60 * 60,
            "1.5 часа": 90 * 60,
            "3 часа": 180 * 60
        }
        self.recent_retention_seconds = mapping.get(self.retention_var.get(), 90 * 60)
        self._save_config()
        self.log(f"Время удержания в буфере «Недавнее»: {self.retention_var.get()}", "SYS")

    def _toggle_monitoring(self):
        self.is_running = not self.is_running
        if self.is_running:
            self.lbl_status.config(text="● SENTINEL ACTIVE", fg="#10b981")
            self.btn_toggle.config(text="⏸ Пауза")
            self.log("Автоматический мониторинг возобновлен.", "INFO")
        else:
            self.lbl_status.config(text="■ PAUSED", fg="#ef4444")
            self.btn_toggle.config(text="▶ Старт")
            self.lbl_timer.config(text="На паузе")
            self.log("Автоматический мониторинг приостановлен.", "WARN")

    def _manual_run(self):
        self.countdown = self.check_interval_seconds
        threading.Thread(target=self._execute_cycle, args=(True,), daemon=True).start()

    def _manual_subsort(self):
        threading.Thread(target=self._deep_subsort, daemon=True).start()

    def _tick_timer(self):
        """Единый синхронизированный таймер без рассинхрона потоков."""
        if self.is_running:
            if self.countdown > 0:
                self.lbl_timer.config(text=f"Цикл через: {self.countdown} с")
                self.countdown -= 1
            else:
                self.countdown = self.check_interval_seconds
                self.lbl_timer.config(text="Сканирование...")
                threading.Thread(target=self._execute_cycle, daemon=True).start()
        self.root.after(1000, self._tick_timer)

    # ── ЯДРО СОРТИРОВКИ ФАЙЛОВ ────────────────────────────────────────────
    def _resolve_unique_path(self, dest_folder: Path, filename: str) -> Path:
        target = dest_folder / filename
        if not target.exists():
            return target
        stem = Path(filename).stem
        suffix = Path(filename).suffix
        counter = 1
        while True:
            new_name = f"{stem} ({counter}){suffix}"
            target = dest_folder / new_name
            if not target.exists():
                return target
            counter += 1

    def _is_file_ready(self, file_path: Path) -> bool:
        if file_path.suffix.lower() in TEMP_EXTENSIONS:
            return False
        try:
            with open(file_path, "ab"):
                pass
            return True
        except (PermissionError, OSError):
            return False

    def _update_stats(self, count=1):
        def _upd():
            self.total_sorted_counter += count
            self.lbl_stats.config(text=f"Сортировано: {self.total_sorted_counter}")
            self._save_config()
        self.root.after(0, _upd)

    def _deep_subsort(self):
        self._set_busy(True)
        all_main_folders = list(CATEGORIES.keys()) + ["Разное"]
        moved = 0

        for cat_name in all_main_folders:
            cat_dir = TARGET_DIR / cat_name
            if not cat_dir.exists() or not cat_dir.is_dir():
                continue

            for item in list(cat_dir.iterdir()):
                if item.is_file() and not item.name.startswith(".") and item.name.lower() not in IGNORED_FILES:
                    if not self._is_file_ready(item):
                        continue

                    ext = item.suffix.lower()
                    sub_folder = ext.lstrip(".") if ext else "без_расширения"
                    target_dir = cat_dir / sub_folder
                    target_dir.mkdir(parents=True, exist_ok=True)

                    dest_file = self._resolve_unique_path(target_dir, item.name)
                    try:
                        shutil.move(str(item), str(dest_file))
                        moved += 1
                        self.log(f"[{cat_name}] {item.name} -> {sub_folder}/", "INFO")
                    except Exception as e:
                        self.log(f"[Err] {item.name}: {e}", "ERR")

        self._set_busy(False)
        if moved > 0:
            self._update_stats(moved)
            self.log(f"✓ Внутренняя сортировка подпапок завершена: {moved} шт.", "INFO")

    def _move_incoming_to_recent(self, folder: Path) -> int:
        recent_dir = folder / RECENT_FOLDER_NAME
        recent_dir.mkdir(exist_ok=True)
        count = 0

        for item in list(folder.iterdir()):
            if item.is_dir() or item.name.startswith(".") or item.name.lower() in IGNORED_FILES:
                continue

            if not self._is_file_ready(item):
                continue

            if self.recent_retention_seconds == 0:
                if self._dispatch_to_category(item, folder):
                    count += 1
                continue

            dest_file = self._resolve_unique_path(recent_dir, item.name)
            try:
                shutil.move(str(item), str(dest_file))
                # Запоминаем точное время попадания файла в буфер «Недавнее»
                self.recent_timestamps[dest_file.name] = time.time()
                count += 1
                self.log(f"В буфер -> Недавнее/{dest_file.name}", "INFO")
            except Exception:
                continue
        return count

    def _dispatch_to_category(self, item: Path, root_folder: Path) -> bool:
        ext = item.suffix.lower()
        sub_folder_name = ext.lstrip(".") if ext else "без_расширения"

        main_category = "Разное"
        for cat_name, extensions in CATEGORIES.items():
            if ext in extensions:
                main_category = cat_name
                break

        target_dir = root_folder / main_category / sub_folder_name
        target_dir.mkdir(parents=True, exist_ok=True)

        dest_file = self._resolve_unique_path(target_dir, item.name)
        try:
            shutil.move(str(item), str(dest_file))
            self._update_stats(1)
            self.log(f"Сортирован -> {main_category}/{sub_folder_name}/{dest_file.name}", "INFO")
            return True
        except Exception:
            return False

    def _sort_mature_files(self, folder: Path) -> int:
        recent_dir = folder / RECENT_FOLDER_NAME
        if not recent_dir.exists():
            return 0

        current_time = time.time()
        count = 0

        for item in list(recent_dir.iterdir()):
            if item.is_dir() or item.name.startswith(".") or item.name.lower() in IGNORED_FILES:
                continue

            if not self._is_file_ready(item):
                continue

            # Берем время помещения в буфер (или время создания/модификации, если программа перезапускалась)
            arrived_time = self.recent_timestamps.get(item.name)
            if arrived_time is None:
                stat = item.stat()
                arrived_time = max(stat.st_ctime, stat.st_mtime)
                self.recent_timestamps[item.name] = arrived_time

            if (current_time - arrived_time) < self.recent_retention_seconds:
                continue

            if self._dispatch_to_category(item, folder):
                self.recent_timestamps.pop(item.name, None)
                count += 1

        return count

    def _execute_cycle(self, manual: bool = False):
        if not self.cycle_lock.acquire(blocking=False):
            return
        try:
            if not TARGET_DIR.exists():
                return
            self._set_busy(True)
            new_cnt = self._move_incoming_to_recent(TARGET_DIR)
            mature_cnt = self._sort_mature_files(TARGET_DIR)
            total_actions = new_cnt + mature_cnt

            if total_actions > 0:
                self.log(f"[Цикл] Обработано и распределено файлов: {total_actions} шт.", "SYS")
            elif manual:
                self.log("[Цикл] Проверка завершена: новых файлов для перемещения нет.", "SYS")
        finally:
            self._set_busy(False)
            self.cycle_lock.release()


if __name__ == "__main__":
    root = tk.Tk()
    app = SentinelOSApp(root)
    root.mainloop()
