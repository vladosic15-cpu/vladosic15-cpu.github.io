import os
import sys
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

# Регистрация AppUserModelID
try:
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Operator.SentinelOS.Core.4.5")
except Exception:
    pass

# Ограничение экземпляров через локальный сокет
SINGLE_INSTANCE_PORT = 49201
try:
    _instance_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    _instance_socket.bind(('127.0.0.1', SINGLE_INSTANCE_PORT))
except OSError:
    sys.exit(0)

APP_NAME = "Sentinel OS"
TARGET_DIR = Path.home() / "Downloads"
RECENT_FOLDER_NAME = "Недавнее"

CATEGORIES = {
    "Аудио": [".mp3", ".wav", ".flac", ".ogg", ".mid", ".aac", ".m4a"],
    "Архивы": [".zip", ".rar", ".7z", ".tar", ".gz", ".iso", ".torrent"],
    "Изображения": [".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".svg", ".ico", ".psd", ".kra"],
    "Видео": [".mp4", ".mkv", ".avi", ".mov", ".webm", ".wmv"],
    "Программы и Скрипты": [".exe", ".msi", ".msixbundle", ".bat", ".cmd", ".ps1", ".py", ".reg", ".apk"],
    "Документы": [".pdf", ".docx", ".doc", ".txt", ".xlsx", ".xls", ".xlsm", ".pptx", ".csv", ".cer"],
    "Моды Minecraft": [".jar"],
}

TEMP_EXTENSIONS = {".crdownload", ".part", ".tmp", ".download"}
IGNORED_FILES = {"desktop.ini", "thumbs.db"}
AUTORUN_REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"

MALICIOUS_PATTERNS = [
    b"powershell -w hidden",
    b"powershell -windowstyle hidden",
    b"downloadstring",
    b"bitsadmin /transfer",
    b"certutil -urlcache",
    b"set-mppreference -disablerealtime",
    b"vssadmin delete shadows",
    b"reg add hkcu\\software\\microsoft\\windows\\currentversion\\run",
    b"rundll32.exe javascript:",
    b"invoke-webrequest -usebasicparsing",
    b"invoke-expression"
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
    ico_path = os.path.join(tempfile.gettempdir(), "sentinel_badge.ico")
    try:
        from PIL import Image, ImageDraw
        img = Image.new("RGBA", (64, 64), color=(0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.polygon([(32, 4), (60, 18), (52, 54), (32, 62), (12, 54), (4, 18)], fill="#090d16", outline="#38bdf8", width=3)
        d.polygon([(32, 14), (48, 22), (42, 46), (32, 52), (22, 46), (16, 22)], fill="#0284c7")
        d.ellipse([(28, 28), (36, 36)], fill="#38bdf8", outline="#ffffff", width=1)
        img.save(ico_path, format="ICO", sizes=[(64, 64), (32, 32), (16, 16)])
        return ico_path
    except Exception:
        return ""


class NatureRelaxWindow:
    def __init__(self, parent):
        self.win = tk.Toplevel(parent)
        self.win.title("Sentinel OS — Зона Спокойствия")
        self.win.geometry("660x490")
        self.win.configure(bg="#070c12")
        self.win.resizable(False, False)
        self.win.attributes("-topmost", True)

        canvas = tk.Canvas(self.win, width=660, height=490, highlightthickness=0)
        canvas.pack(fill=tk.BOTH, expand=True)

        canvas.create_rectangle(0, 0, 660, 260, fill="#38bdf8", outline="")
        for cx, cy in [(140, 70), (170, 65), (200, 70), (450, 90), (480, 85), (510, 90)]:
            canvas.create_oval(cx-25, cy-18, cx+25, cy+18, fill="#ffffff", outline="")

        sx, sy, r = 85, 85, 38
        for angle in range(0, 360, 30):
            rad = math.radians(angle)
            canvas.create_line(sx + math.cos(rad)*(r+4), sy + math.sin(rad)*(r+4),
                               sx + math.cos(rad)*(r+22), sy + math.sin(rad)*(r+22), fill="#facc15", width=3)
        canvas.create_oval(sx - r, sy - r, sx + r, sy + r, fill="#fde047", outline="#eab308", width=2)

        canvas.create_oval(-80, 160, 420, 370, fill="#15803d", outline="")
        canvas.create_oval(260, 170, 760, 380, fill="#166534", outline="")
        canvas.create_rectangle(0, 250, 660, 490, fill="#22c55e", outline="")

        river_points = [(300, 240), (340, 240), (390, 310), (440, 370), (430, 430), (390, 490),
                        (290, 490), (320, 420), (310, 350), (270, 290)]
        canvas.create_polygon(river_points, fill="#0284c7", outline="#38bdf8", width=2, smooth=True)

        for fx, fy in [(60, 320), (120, 390), (190, 300), (230, 430), (530, 330), (590, 400), (490, 450)]:
            canvas.create_oval(fx-4, fy-4, fx+4, fy+4, fill="#f43f5e", outline="")
            canvas.create_oval(fx-1, fy-1, fx+1, fy+1, fill="#fef08a", outline="")

        canvas.create_text(330, 465, text="✨ Всё в порядке. Рабочий стол чист ✨", fill="#ffffff", font=("Segoe UI", 11, "bold"))


class HardwareDiagWindow:
    def __init__(self, parent):
        self.win = tk.Toplevel(parent)
        self.win.title("Sentinel OS — Телеметрия Системы")
        self.win.geometry("680x560")
        self.win.configure(bg="#080a0c")
        self.win.resizable(False, False)
        self.win.attributes("-topmost", True)

        header = tk.Frame(self.win, bg="#0f172a", padx=16, pady=12)
        header.pack(fill=tk.X)

        tk.Label(
            header,
            text="⚡ АППАРАТНАЯ ТЕЛЕМЕТРИЯ И РЕСУРСЫ",
            fg="#38bdf8",
            bg="#0f172a",
            font=("Consolas", 12, "bold")
        ).pack(side=tk.LEFT)

        self.text_box = tk.Text(
            self.win,
            bg="#050709",
            fg="#34d399",
            font=("Consolas", 11),
            relief="flat",
            padx=16,
            pady=14
        )
        self.text_box.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
        self._load_specs()

    def _load_specs(self):
        specs = []
        specs.append(f"• Операционная система: {get_accurate_os_name()}")
        specs.append(f"• Архитектура: {os.environ.get('PROCESSOR_ARCHITECTURE', 'AMD64')}")

        try:
            import psutil
            cpu_name = get_cpu_brand_name()
            cores = psutil.cpu_count(logical=False)
            threads = psutil.cpu_count(logical=True)
            usage = psutil.cpu_percent(interval=0.2)
            specs.append(f"\n[ ПРОЦЕССОР (CPU) ]")
            specs.append(f"• Модель: {cpu_name}")
            specs.append(f"• Ядра / Потоки: {cores}C / {threads}T | Нагрузка: {usage}%")

            ram = psutil.virtual_memory()
            specs.append(f"\n[ ОПЕРАТИВНАЯ ПАМЯТЬ (RAM) ]")
            specs.append(f"• Всего ОЗУ: {round(ram.total / (1024**3), 1)} GB")
            specs.append(f"• Свободно: {round(ram.free / (1024**3), 1)} GB ({ram.percent}% занято)")

            specs.append(f"\n[ НАКОПИТЕЛИ И ДИСКИ ]")
            for part in psutil.disk_partitions(all=False):
                try:
                    u = psutil.disk_usage(part.mountpoint)
                    specs.append(f"• Диск {part.device} [{part.fstype}] -> Доступно: {u.free // (1024**3)} GB из {u.total // (1024**3)} GB ({u.percent}% занято)")
                except PermissionError:
                    continue
        except ImportError:
            specs.append("\n[!] Модуль psutil обновляется...")

        specs.append(f"\n[ ВИДЕОКАРТА (GPU) ]")
        try:
            cmd = "powershell \"Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name\""
            gpu = subprocess.check_output(cmd, shell=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW).strip()
            specs.append(f"• GPU: {gpu if gpu else 'Стандартный графический адаптер'}")
        except Exception:
            specs.append("• GPU: Информация недоступна")

        self.text_box.delete("1.0", tk.END)
        self.text_box.insert(tk.END, "\n".join(specs))


class SentinelOSApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME)
        
        # Разворачиваем окно на весь экран при старте
        self.root.state("zoomed")
        self.root.minsize(980, 680)
        self.root.configure(bg="#060b13")

        self.is_running = True
        self.check_interval_seconds = 60
        self.recent_retention_seconds = 90 * 60
        self.countdown = self.check_interval_seconds
        self.total_sorted_counter = 0

        self.tray_icon = None
        self.pystray_ready = False
        self.ico_path = ""

        # Переменные для анимаций
        self.pulse_step = 0
        self.is_busy = False
        self.busy_pos = 0

        self._init_theme()
        self._build_gradient_background()
        self._build_ui()

        # Запуск анимации пульсации статуса
        self._animate_pulse()

        threading.Thread(target=self._bootstrap_environment, daemon=True).start()

    def _init_theme(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure("Dark.TCombobox",
                        fieldbackground="#131e2e",
                        background="#0b1420",
                        foreground="#38bdf8",
                        darkcolor="#131e2e",
                        lightcolor="#131e2e",
                        selectbackground="#131e2e",
                        selectforeground="#38bdf8",
                        arrowcolor="#38bdf8",
                        bordercolor="#223954")
        
        style.map("Dark.TCombobox",
                  fieldbackground=[("readonly", "#131e2e"), ("focus", "#131e2e")],
                  selectbackground=[("readonly", "#131e2e")],
                  selectforeground=[("readonly", "#38bdf8")],
                  foreground=[("readonly", "#38bdf8")])

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
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        if width <= 1 or height <= 1:
            return

        self.bg_canvas.delete("grad")
        steps = 40
        c1 = (5, 10, 18)
        c2 = (17, 28, 45)

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
        """Создает кнопку с плавной сменой цвета при наведении курсора."""
        btn = tk.Button(
            parent,
            text=text,
            bg=bg,
            fg=fg,
            relief="flat",
            padx=padx,
            pady=pady,
            font=("Segoe UI", 9, "bold"),
            cursor="hand2",
            command=cmd
        )
        btn.bind("<Enter>", lambda e: btn.config(bg=hover_bg))
        btn.bind("<Leave>", lambda e: btn.config(bg=bg))
        return btn

    def _animate_pulse(self):
        """Анимация дыхания для зеленого индикатора статуса."""
        if self.is_running:
            self.pulse_step = (self.pulse_step + 1) % 10
            pulse_colors = [
                "#10b981", "#22c55e", "#4ade80", "#86efac", "#4ade80", 
                "#22c55e", "#10b981", "#059669", "#047857", "#059669"
            ]
            self.lbl_status.config(fg=pulse_colors[self.pulse_step])
        self.root.after(140, self._animate_pulse)

    def _animate_busy_bar(self):
        """Бегущая неоновая анимация сканирования."""
        if self.is_busy:
            w = self.scan_bar_canvas.winfo_width()
            self.busy_pos = (self.busy_pos + 18) % (w + 140)
            self.scan_bar_canvas.delete("wave")
            self.scan_bar_canvas.create_rectangle(
                self.busy_pos - 120, 0, self.busy_pos, 4,
                fill="#38bdf8", outline="", tags="wave"
            )
            self.root.after(30, self._animate_busy_bar)
        else:
            self.scan_bar_canvas.delete("wave")

    def _set_busy(self, status: bool):
        self.is_busy = status
        if status:
            self._animate_busy_bar()

    def _build_ui(self):
        content = tk.Frame(self.root, bg="#060b13")
        content.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)

        # 1. Верхний информационный блок
        header = tk.Frame(content, bg="#0d1826", padx=18, pady=10, highlightthickness=1, highlightbackground="#1e344f")
        header.pack(fill=tk.X, pady=(0, 4))

        self.lbl_status = tk.Label(
            header, 
            text="● SENTINEL ACTIVE", 
            fg="#10b981", 
            bg="#0d1826", 
            font=("Consolas", 13, "bold")
        )
        self.lbl_status.pack(side=tk.LEFT)

        self.lbl_stats = tk.Label(
            header,
            text="Сортировано файлов: 0",
            fg="#cbd5e1",
            bg="#0d1826",
            font=("Segoe UI", 10, "bold")
        )
        self.lbl_stats.pack(side=tk.LEFT, padx=30)

        self.lbl_timer = tk.Label(
            header, 
            text="Следующий цикл: 60 с", 
            fg="#38bdf8", 
            bg="#0d1826", 
            font=("Consolas", 11, "bold")
        )
        self.lbl_timer.pack(side=tk.RIGHT)

        # 2. Панель параметров времени
        cfg_panel = tk.Frame(content, bg="#0a121c", padx=16, pady=8, highlightthickness=1, highlightbackground="#1b2e45")
        cfg_panel.pack(fill=tk.X, pady=3)

        tk.Label(cfg_panel, text="⏱ Тайминг:", bg="#0a121c", fg="#94a3b8", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(0, 6))

        self.interval_var = tk.StringVar(value="60 сек")
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

        tk.Label(cfg_panel, text="⏳ Буфер Недавнего:", bg="#0a121c", fg="#94a3b8", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(0, 6))

        self.retention_var = tk.StringVar(value="1.5 часа")
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

        self.btn_autostart = self._create_hover_btn(
            cfg_panel,
            text=self._get_autostart_label(),
            bg="#131e2e" if not self._is_autostart_enabled() else "#065f46",
            fg="#38bdf8" if not self._is_autostart_enabled() else "#34d399",
            hover_bg="#1d2e46" if not self._is_autostart_enabled() else "#047857",
            cmd=self._toggle_autostart,
            padx=12,
            pady=3
        )
        self.btn_autostart.pack(side=tk.RIGHT)

        # 3. АДАПТИВНАЯ ПАНЕЛЬ КНОПОК
        # Ряд 1: Главные действия
        row1_panel = tk.Frame(content, bg="#060b13")
        row1_panel.pack(fill=tk.X, pady=3)

        self._create_hover_btn(row1_panel, "⚡ Сортировать", "#0284c7", "#ffffff", "#0369a1", self._manual_run).pack(side=tk.LEFT, padx=(0, 4))
        self._create_hover_btn(row1_panel, "🔨 Внутри папок", "#2563eb", "#ffffff", "#1d4ed8", self._manual_subsort).pack(side=tk.LEFT, padx=4)
        self._create_hover_btn(row1_panel, "🎯 Удалить дубли (MD5)", "#334155", "#f8fafc", "#475569", lambda: threading.Thread(target=self._find_and_delete_duplicates, daemon=True).start()).pack(side=tk.LEFT, padx=4)
        self._create_hover_btn(row1_panel, "🛡 Антивирус OS", "#dc2626", "#ffffff", "#b91c1c", lambda: threading.Thread(target=self._deep_system_security_scan, daemon=True).start()).pack(side=tk.LEFT, padx=4)
        self._create_hover_btn(row1_panel, "🔍 Железо ПК", "#475569", "#ffffff", "#64748b", lambda: HardwareDiagWindow(self.root)).pack(side=tk.LEFT, padx=4)

        # Правые кнопки ряда 1
        self._create_hover_btn(row1_panel, "📥 В трей", "#059669", "#ffffff", "#047857", self.hide_to_tray).pack(side=tk.RIGHT, padx=(4, 0))
        self.btn_toggle = self._create_hover_btn(row1_panel, "⏸ Пауза", "#1e293b", "#f1f5f9", "#334155", self._toggle_monitoring)
        self.btn_toggle.pack(side=tk.RIGHT, padx=4)

        # Ряд 2: Быстрый доступ и оптимизация
        row2_panel = tk.Frame(content, bg="#060b13")
        row2_panel.pack(fill=tk.X, pady=3)

        self._create_hover_btn(row2_panel, "🧹 Очистить Temp", "#1e293b", "#cbd5e1", "#334155", lambda: threading.Thread(target=self._clean_temp_files, daemon=True).start(), padx=10, pady=4).pack(side=tk.LEFT, padx=(0, 4))
        self._create_hover_btn(row2_panel, "⚡ Рестарт GPU", "#991b1b", "#ffffff", "#7f1d1d", self._restart_graphics_driver, padx=10, pady=4).pack(side=tk.LEFT, padx=4)
        self._create_hover_btn(row2_panel, "☀️ Релакс", "#eab308", "#000000", "#ca8a04", lambda: NatureRelaxWindow(self.root), padx=10, pady=4).pack(side=tk.LEFT, padx=4)

        self._create_hover_btn(row2_panel, "📂 Загрузки", "#0f172a", "#94a3b8", "#1e293b", lambda: self._open_dir(TARGET_DIR), padx=10, pady=4).pack(side=tk.RIGHT, padx=(4, 0))
        self._create_hover_btn(row2_panel, "📁 Недавнее", "#0f172a", "#94a3b8", "#1e293b", lambda: self._open_dir(TARGET_DIR / RECENT_FOLDER_NAME), padx=10, pady=4).pack(side=tk.RIGHT, padx=4)

        # 4. Зеленый терминал
        terminal_frame = tk.Frame(content, bg="#030608", highlightthickness=1, highlightbackground="#132b1f")
        terminal_frame.pack(fill=tk.BOTH, expand=True, pady=(4, 2))

        self.log_text = tk.Text(
            terminal_frame, 
            bg="#030608", 
            fg="#34d399", 
            insertbackground="#34d399",
            font=("Consolas", 11), 
            relief="flat", 
            padx=14, 
            pady=12
        )
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(terminal_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar.set)

        # Анимированная полоса сканирования
        self.scan_bar_canvas = tk.Canvas(content, height=4, bg="#060b13", highlightthickness=0)
        self.scan_bar_canvas.pack(fill=tk.X, pady=(1, 3))

        # 5. Панель ввода
        cmd_input_frame = tk.Frame(content, bg="#07140e", highlightthickness=1, highlightbackground="#184227")
        cmd_input_frame.pack(fill=tk.X, pady=(0, 2))

        lbl_prompt = tk.Label(
            cmd_input_frame, 
            text="Sentinel:~$ ", 
            fg="#4ade80", 
            bg="#07140e", 
            font=("Consolas", 11, "bold")
        )
        lbl_prompt.pack(side=tk.LEFT, padx=(10, 0), pady=6)

        self.cmd_entry = tk.Entry(
            cmd_input_frame, 
            bg="#07140e", 
            fg="#a7f3d0", 
            insertbackground="#4ade80", 
            relief="flat", 
            font=("Consolas", 11)
        )
        self.cmd_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8, pady=6)
        self.cmd_entry.bind("<Return>", self._handle_terminal_cmd)

        self.root.protocol("WM_DELETE_WINDOW", self.hide_to_tray)

    def log(self, message: str):
        now = datetime.now().strftime("%H:%M:%S")
        entry = f"[{now}] {message}\n"
        self.log_text.insert(tk.END, entry)
        self.log_text.see(tk.END)

    def _deep_system_security_scan(self):
        self.root.after(0, lambda: self._set_busy(True))
        self.log(">> [SENTINEL-AV] Старт углубленного аудита системы...")
        threats_found = []

        # 1. Hosts
        self.log(">> [1/5] Проверка системного маршрутизатора (hosts)...")
        hosts_path = Path(r"C:\Windows\System32\drivers\etc\hosts")
        if hosts_path.exists():
            try:
                with open(hosts_path, "r", encoding="utf-8", errors="ignore") as f:
                    hosts_text = f.read().lower()
                    for blocked in ["kaspersky", "drweb", "malwarebytes", "virustotal", "avast"]:
                        if blocked in hosts_text and ("127.0.0.1" in hosts_text or "0.0.0.0" in hosts_text):
                            threats_found.append((hosts_path, f"Блокировка доступа к {blocked} в hosts"))
            except Exception:
                pass

        # 2. Реестр автозагрузки
        self.log(">> [2/5] Сканирование ключей автозагрузки реестра...")
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
                        if "temp" in v_lower or "powershell" in v_lower or "wscript" in v_lower:
                            self.root.after(0, self.log, f"  [!] Автозапуск: {name} -> {val}")
                            threats_found.append((Path(str(val)), f"Подозрительный ключ: {name}"))
            except Exception:
                pass

        # 3. Активные процессы
        self.log(">> [3/5] Анализ запущенных процессов в RAM...")
        try:
            import psutil
            for proc in psutil.process_iter(['pid', 'name', 'exe']):
                try:
                    exe = (proc.info['exe'] or "").lower()
                    if exe and ("appdata\\local\\temp" in exe or "appdata\\roaming" in exe) and not "python" in exe:
                        if exe.endswith((".exe", ".vbs", ".bat", ".cmd")):
                            self.root.after(0, self.log, f"  [!] Процесс из профиля: PID {proc.info['pid']} ({proc.info['name']})")
                            threats_found.append((Path(exe), f"Активный процесс из Temp/AppData [PID {proc.info['pid']}]"))
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception:
            pass

        # 4. Файлы на диске
        self.log(">> [4/5] Побайтовое сканирование накопителя на маскировку и пейлоады...")
        startup_dir = Path(os.environ.get("APPDATA", "")) / r"Microsoft\Windows\Start Menu\Programs\Startup"
        scan_targets = [TARGET_DIR, Path(tempfile.gettempdir()), startup_dir]
        fake_ext_pattern = [".pdf.exe", ".jpg.exe", ".png.exe", ".docx.exe", ".xlsx.exe", ".txt.vbs", ".doc.scr"]

        scanned_files = 0
        for s_dir in scan_targets:
            if not s_dir.exists():
                continue
            for file_path in s_dir.rglob("*"):
                if not file_path.is_file() or file_path.suffix.lower() in TEMP_EXTENSIONS:
                    continue

                scanned_files += 1
                if scanned_files % 150 == 0:
                    self.root.after(0, self.log, f"  Проверено объектов: {scanned_files}...")

                fname_lower = file_path.name.lower()
                for bad_combo in fake_ext_pattern:
                    if fname_lower.endswith(bad_combo):
                        threats_found.append((file_path, f"Маскировка двойного расширения: {bad_combo}"))
                        break

                if "\u202e" in file_path.name:
                    threats_found.append((file_path, "Обнаружен скрытый символ Right-to-Left Override"))

                if file_path.suffix.lower() in [".bat", ".cmd", ".ps1", ".vbs", ".js"]:
                    try:
                        with open(file_path, "rb") as f:
                            content = f.read(250000).lower()
                            for pattern in MALICIOUS_PATTERNS:
                                if pattern in content:
                                    threats_found.append((file_path, f"Деструктивный паттерн: {pattern.decode('latin1', errors='ignore')}"))
                                    break
                    except Exception:
                        pass

        # 5. Итог
        self.log(f">> [5/5] Завершено. Проверено файлов: {scanned_files}")
        self.root.after(0, lambda: self._set_busy(False))

        if not threats_found:
            self.log("✓ [SENTINEL-AV] Угроз не обнаружено. Память, реестр и файлы чисты.")
            return

        self.log(f"⚠️ [ТРЕВОГА] Обнаружено подозрительных объектов: {len(threats_found)}")
        for path, reason in threats_found:
            self.log(f"  [!] {path.name} -> {reason}")

        res = messagebox.askyesno(
            "Sentinel OS — Защитник Системы", 
            f"Обнаружено {len(threats_found)} угроз/подозрительных объектов.\n\n"
            "Изолировать найденные файлы в карантин (Quarantine)?"
        )
        if res:
            q_dir = TARGET_DIR / "Quarantine"
            q_dir.mkdir(exist_ok=True)
            for path, _ in threats_found:
                try:
                    if path.is_file():
                        shutil.move(str(path), str(q_dir / path.name))
                        self.log(f"🔒 Изолирован: {path.name}")
                except Exception as e:
                    self.log(f"[x] Ошибка изоляции {path.name}: {e}")

    def _find_and_delete_duplicates(self):
        self.root.after(0, lambda: self._set_busy(True))
        self.log(">> Поиск и очистка дубликатов по алгоритму MD5...")
        hashes = {}
        duplicates_removed = 0
        freed_bytes = 0

        def get_file_md5(p: Path):
            hasher = hashlib.md5()
            with open(p, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()

        for file_path in list(TARGET_DIR.rglob("*")):
            if file_path.is_file() and file_path.suffix.lower() not in TEMP_EXTENSIONS and file_path.name.lower() not in IGNORED_FILES:
                try:
                    f_hash = get_file_md5(file_path)
                    if f_hash in hashes:
                        orig = hashes[f_hash]
                        file_size = file_path.stat().st_size
                        try:
                            file_path.unlink()
                            duplicates_removed += 1
                            freed_bytes += file_size
                            self.root.after(0, self.log, f"[Удалён дубликат] «{file_path.name}» (копия «{orig.name}»)")
                        except Exception as e:
                            self.root.after(0, self.log, f"[Err] {file_path.name}: {e}")
                    else:
                        hashes[f_hash] = file_path
                except Exception:
                    continue

        self.root.after(0, lambda: self._set_busy(False))
        if duplicates_removed == 0:
            self.log("✓ Проверка завершена: дубликатов не найдено.")
        else:
            freed_mb = round(freed_bytes / (1024 * 1024), 2)
            self.log(f"★ Удалено дубликатов: {duplicates_removed} шт. | Освобождено: {freed_mb} MB")

    def _clean_temp_files(self):
        temp_dir = Path(tempfile.gettempdir())
        self.log(f">> Очистка временных файлов: {temp_dir}")
        deleted_count = 0
        freed_bytes = 0

        for item in list(temp_dir.iterdir()):
            try:
                if item.is_file():
                    size = item.stat().st_size
                    item.unlink()
                    deleted_count += 1
                    freed_bytes += size
                elif item.is_dir():
                    shutil.rmtree(item, ignore_errors=True)
            except Exception:
                continue

        freed_mb = round(freed_bytes / (1024 * 1024), 2)
        self.log(f"✓ Temp очищен! Удалено файлов: {deleted_count} | Освобождено: {freed_mb} MB")

    def _restart_graphics_driver(self):
        self.log(">> Инициирован сброс графического адаптера...")
        try:
            cmd = "powershell -Command \"(Get-WmiObject Win32_VideoController).Name\""
            subprocess.Popen(cmd, shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
            self.log("✓ Сигнал ресета видеоподсистемы передан драйверу.")
        except Exception as e:
            self.log(f"[x] Ошибка: {e}")

    def _bootstrap_environment(self):
        self.log(f">> Инициализация {APP_NAME}...")

        self.ico_path = generate_app_icon_file()
        if self.ico_path and os.path.exists(self.ico_path):
            try:
                self.root.iconbitmap(self.ico_path)
            except Exception:
                pass

        required = {"pystray": "pystray", "PIL": "pillow", "psutil": "psutil"}
        missing = []

        for mod, pip_name in required.items():
            try:
                __import__(mod)
            except ImportError:
                missing.append(pip_name)

        if missing:
            self.log(f"(!) Доустановка библиотек: {', '.join(missing)}")
            py_bin = get_console_python_path()
            for pkg in missing:
                self.log(f">> Загрузка пакета {pkg} через pip...")
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
                            self.root.after(0, self.log, f"  pip: {line.strip()}")
                    proc.wait()
                    if proc.returncode == 0:
                        self.log(f"✓ {pkg} готов!")
                except Exception as e:
                    self.log(f"[x] Ошибка: {e}")

        self._init_tray_safe()

        self.root.after(0, lambda: self.lbl_status.config(text="● SENTINEL ACTIVE", fg="#10b981"))
        self.root.after(0, lambda: self.lbl_timer.config(text=f"Следующий цикл: {self.countdown} с"))
        self.log(">> Ядро активировано. Введите 'help' в терминал для команд.")

        threading.Thread(target=self._monitor_loop, daemon=True).start()
        threading.Thread(target=self._deep_subsort, daemon=True).start()
        self._tick_timer()

    def _init_tray_safe(self):
        try:
            import pystray
            from PIL import Image

            if self.ico_path and os.path.exists(self.ico_path):
                img = Image.open(self.ico_path)
            else:
                img = Image.new("RGBA", (64, 64), color=(16, 185, 129))

            menu = pystray.Menu(
                pystray.MenuItem("Развернуть Sentinel", self.show_from_tray, default=True),
                pystray.MenuItem("Сортировать сейчас", lambda: self._manual_run()),
                pystray.MenuItem("Выход", self._quit_app)
            )
            self.tray_icon = pystray.Icon(APP_NAME, img, "Sentinel OS", menu)
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
        if self.tray_icon:
            self.tray_icon.stop()
        self.root.destroy()
        sys.exit(0)

    def _open_dir(self, path: Path):
        path.mkdir(exist_ok=True)
        os.startfile(path)

    def _is_autostart_enabled(self) -> bool:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTORUN_REG_KEY, 0, winreg.KEY_READ) as key:
                val, _ = winreg.QueryValueEx(key, APP_NAME)
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
                    winreg.DeleteValue(key, APP_NAME)
                except FileNotFoundError:
                    pass
                self.log("Автозагрузка Windows отключена.")
            else:
                pythonw_exe = Path(sys.executable).parent / "pythonw.exe"
                exec_bin = pythonw_exe if pythonw_exe.exists() else Path(sys.executable)
                cmd = f'"{exec_bin}" "{script_path}"'
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
                self.log("Sentinel OS прописан в автозагрузку Windows.")

        is_now_on = self._is_autostart_enabled()
        self.btn_autostart.config(
            text=self._get_autostart_label(),
            bg="#065f46" if is_now_on else "#131e2e",
            fg="#34d399" if is_now_on else "#38bdf8"
        )

    def _handle_terminal_cmd(self, event=None):
        raw_cmd = self.cmd_entry.get().strip()
        self.cmd_entry.delete(0, tk.END)
        if not raw_cmd:
            return

        self.log(f">> {raw_cmd}")
        root_cmd = raw_cmd.split()[0].lower()

        if root_cmd in ("operator", "opetator", "оператор", "vladosic"):
            self.log("★ [СЕКРЕТНЫЙ ПРОТОКОЛ] Приветствую, Operator. Все узлы и накопители под контролем.")
        elif root_cmd in ("bio", "rapture", "bioshock"):
            self.log("★ [RAPTURE] «No Gods or Kings. Only Man.» — Добро пожаловать на борт, мастер.")
        elif root_cmd in ("rats", "cheese", "крысы"):
            self.log("★ Принц и Толик одобрили текущий порядок в файловой системе!")
        elif root_cmd == "matrix":
            self._easter_egg_matrix()
        elif root_cmd in ("relax", "солнце", "полянка"):
            NatureRelaxWindow(self.root)
        elif root_cmd in ("scan-av", "antivirus", "защита"):
            threading.Thread(target=self._deep_system_security_scan, daemon=True).start()
        elif root_cmd in ("help", "?"):
            self.log("Команды Sentinel OS:")
            self.log("  sort      - глубокая сортировка подпапок")
            self.log("  scan      - проверить папку Downloads прямо сейчас")
            self.log("  antivirus - глубокий аудит системы на трояны/майнеры")
            self.log("  relax     - открыть арт-зону релакса")
            self.log("  clean     - очистить файлы Temp")
            self.log("  dups      - поиск и удаление дубликатов по MD5")
            self.log("  specs     - телеметрия железа и ОС")
            self.log("  cls       - очистить консоль")
            self.log("  open      - открыть Загрузки")
            self.log("  <cmd>     - любая команда Windows")
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
                line = "".join(random.choice(chars) for _ in range(54))
                self.root.after(0, self.log, f"  {line}")
                time.sleep(0.05)
            self.root.after(0, self.log, "★ Matrix sub-routine finished.")
        threading.Thread(target=stream, daemon=True).start()

    def _run_system_cmd(self, cmd: str):
        try:
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding="cp866")
            output = res.stdout if res.stdout else res.stderr
            for line in output.splitlines():
                if line.strip():
                    self.root.after(0, self.log, f"  {line}")
        except Exception as e:
            self.root.after(0, self.log, f"Ошибка выполнения: {e}")

    def _on_interval_change(self, event=None):
        mapping = {"30 сек": 30, "60 сек": 60, "2 мин": 120, "5 мин": 300}
        self.check_interval_seconds = mapping.get(self.interval_var.get(), 60)
        self.countdown = self.check_interval_seconds
        self.log(f"Интервал сканирования: {self.interval_var.get()}")

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
        self.log(f"Буфер «Недавнее»: {self.retention_var.get()}")

    def _toggle_monitoring(self):
        self.is_running = not self.is_running
        if self.is_running:
            self.lbl_status.config(text="● SENTINEL ACTIVE", fg="#10b981")
            self.btn_toggle.config(text="⏸ Пауза")
            self.log("Мониторинг запущен.")
        else:
            self.lbl_status.config(text="■ PAUSED", fg="#ef4444")
            self.btn_toggle.config(text="▶ Возобновить")
            self.lbl_timer.config(text="Остановлен")
            self.log("Мониторинг приостановлен.")

    def _manual_run(self):
        self.countdown = self.check_interval_seconds
        threading.Thread(target=self._execute_cycle, daemon=True).start()

    def _manual_subsort(self):
        threading.Thread(target=self._deep_subsort, daemon=True).start()

    def _tick_timer(self):
        if self.is_running:
            if self.countdown > 0:
                self.lbl_timer.config(text=f"Следующий цикл: {self.countdown} с")
                self.countdown -= 1
            else:
                self.countdown = self.check_interval_seconds
        self.root.after(1000, self._tick_timer)

    def _monitor_loop(self):
        while True:
            if self.is_running:
                self._execute_cycle()
            time.sleep(self.check_interval_seconds)

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
        self.total_sorted_counter += count
        self.lbl_stats.config(text=f"Сортировано файлов: {self.total_sorted_counter}")

    def _deep_subsort(self):
        self.root.after(0, lambda: self._set_busy(True))
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
                        self.root.after(0, self.log, f"[{cat_name}] {item.name} -> {sub_folder}/")
                    except Exception as e:
                        self.root.after(0, self.log, f"[Err] {item.name}: {e}")

        self.root.after(0, lambda: self._set_busy(False))
        if moved > 0:
            self.root.after(0, self._update_stats, moved)
            self.root.after(0, self.log, f"✓ Разобрано внутри папок: {moved} шт.")

    def _move_incoming_to_recent(self, folder: Path) -> int:
        recent_dir = folder / RECENT_FOLDER_NAME
        recent_dir.mkdir(exist_ok=True)
        count = 0

        for item in folder.iterdir():
            if item.is_dir() or item.name.startswith(".") or item.name.lower() in IGNORED_FILES:
                continue

            if not self._is_file_ready(item):
                continue

            if self.recent_retention_seconds == 0:
                self._dispatch_to_category(item, folder)
                count += 1
                continue

            dest_file = self._resolve_unique_path(recent_dir, item.name)
            try:
                shutil.move(str(item), str(dest_file))
                count += 1
                self.root.after(0, self.log, f"Новый файл -> Недавнее/{item.name}")
            except Exception:
                continue
        return count

    def _dispatch_to_category(self, item: Path, root_folder: Path):
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
            self.root.after(0, self._update_stats, 1)
            self.root.after(0, self.log, f"Файл -> {main_category}/{sub_folder_name}/{item.name}")
        except Exception:
            pass

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

            if (current_time - item.stat().st_mtime) < self.recent_retention_seconds:
                continue

            ext = item.suffix.lower()
            sub_folder_name = ext.lstrip(".") if ext else "без_расширения"

            main_category = "Разное"
            for cat_name, extensions in CATEGORIES.items():
                if ext in extensions:
                    main_category = cat_name
                    break

            target_dir = folder / main_category / sub_folder_name
            target_dir.mkdir(parents=True, exist_ok=True)

            dest_file = self._resolve_unique_path(target_dir, item.name)
            try:
                shutil.move(str(item), str(dest_file))
                count += 1
                self.root.after(0, self._update_stats, 1)
                self.root.after(
                    0, 
                    self.log, 
                    f"Истёк буфер: {item.name} -> {main_category}/{sub_folder_name}/"
                )
            except Exception:
                continue
        return count

    def _execute_cycle(self):
        if not TARGET_DIR.exists():
            return
        new_cnt = self._move_incoming_to_recent(TARGET_DIR)
        mature_cnt = self._sort_mature_files(TARGET_DIR)
        total_actions = new_cnt + mature_cnt
        if total_actions > 0:
            self.root.after(0, self.log, f"[Автоцикл] Завершено. Перемещено файлов: {total_actions}")
        else:
            self.root.after(0, self.log, "[Автоцикл] Проверка завершена: новых файлов нет.")


if __name__ == "__main__":
    root = tk.Tk()
    app = SentinelOSApp(root)
    root.mainloop()