@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul
title Sentinel OS :: Core Deployment & Launcher Deck v5.0
mode con: cols=92 lines=36

:: ============================================================================
:: ИНИЦИАЛИЗАЦИЯ ANSI-ПАЛИТРЫ SENTINEL OS (WINDOWS 10/11)
:: ============================================================================
for /F "tokens=1,2 delims=#" %%a in ('"prompt #$H#$E# & echo on & for %%b in (1) do rem"') do (
    set "ESC=%%b"
)

set "C_RESET=%ESC%[0m"
set "C_CYAN=%ESC%[96m"
set "C_BLUE=%ESC%[94m"
set "C_GREEN=%ESC%[92m"
set "C_YELLOW=%ESC%[93m"
set "C_RED=%ESC%[91m"
set "C_PURPLE=%ESC%[95m"
set "C_GRAY=%ESC%[90m"
set "C_WHITE=%ESC%[97m"
set "C_BOLD=%ESC%[1m"

cd /d "%~dp0"

:BOOT_HEADER
cls
echo %C_CYAN%╔════════════════════════════════════════════════════════════════════════════════════════╗%C_RESET%
echo %C_CYAN%║%C_RESET%  %C_BOLD%%C_WHITE%SENTINEL OS :: CORE DEPLOYMENT ^& ENVIRONMENT MATRIX v5.0%C_RESET%                              %C_CYAN%║%C_RESET%
echo %C_CYAN%║%C_RESET%  %C_PURPLE%Operator Access Verified%C_RESET% %C_GRAY%│%C_RESET% %C_CYAN%Node: %COMPUTERNAME%%C_RESET% %C_GRAY%│%C_RESET% %C_GREEN%Target: Python 3.10+ (x64)%C_RESET%         %C_CYAN%║%C_RESET%
echo %C_CYAN%╚════════════════════════════════════════════════════════════════════════════════════════╝%C_RESET%
echo.

:: ============================================================================
:: ЭТАП 1. ПОИСК И ВЕРИФИКАЦИЯ PYTHON (ЗАЩИТА ОТ MICROSOFT STORE STUB)
:: ============================================================================
echo %C_BLUE%[1/3]%C_RESET% %C_WHITE%Сканирование системного интерпретатора Python...%C_RESET%

set "PY_CMD="
set "PYW_CMD="

:: Проверяем стандартный python в PATH (исключая пустую заглушку WindowsApps)
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
if !errorlevel! equ 0 (
    set "PY_CMD=python"
    goto :PYTHON_FOUND
)

:: Проверяем системный лаунчер py.exe
py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
if !errorlevel! equ 0 (
    set "PY_CMD=py -3"
    goto :PYTHON_FOUND
)

:: Ищем в стандартных папках установки LocalAppData
for %%V in (313 312 311 310) do (
    if exist "%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe" (
        set "PATH=%LOCALAPPDATA%\Programs\Python\Python%%V;%LOCALAPPDATA%\Programs\Python\Python%%V\Scripts;!PATH!"
        set "PY_CMD=%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe"
        goto :PYTHON_FOUND
    )
)

goto :INSTALL_PYTHON

:PYTHON_FOUND
for /f "delims=" %%v in ('!PY_CMD! -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')"') do set "PY_VER=%%v"
for /f "delims=" %%p in ('!PY_CMD! -c "import sys; print(sys.executable)"') do set "PY_EXE_PATH=%%p"
for %%i in ("!PY_EXE_PATH!") do set "PYW_CMD=%%~dpipythonw.exe"

echo   %C_GREEN%[✓] Обнаружен рабочий Python:%C_RESET% %C_CYAN%v!PY_VER!%C_RESET%
echo   %C_GRAY%    Путь: !PY_EXE_PATH!%C_RESET%

:: Проверка наличия модуля Tkinter (tcl/tk)
!PY_CMD! -c "import tkinter" >nul 2>&1
if !errorlevel! neq 0 (
    echo   %C_RED%[!] Внимание: Модуль графики Tkinter не найден в текущей сборке Python!%C_RESET%
    goto :INSTALL_PYTHON
)
echo   %C_GREEN%[✓] Графическое ядро Tkinter (Tcl/Tk) активно.%C_RESET%
goto :CHECK_DEPS

:: ============================================================================
:: АВТОМАТИЧЕСКАЯ ЗАГРУЗКА И ТИХАЯ УСТАНОВКА PYTHON 3.11.9 (x64)
:: ============================================================================
:INSTALL_PYTHON
echo.
echo   %C_YELLOW%[!] Подходящий Python (^>= 3.10) не найден в системе.%C_RESET%
echo   %C_CYAN%[»] Инициализация загрузки официального пакета Python 3.11.9 (64-bit)...%C_RESET%

set "INSTALLER_URL=https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe"
set "INSTALLER_PATH=%TEMP%\sentinel_python_setup.exe"

:: Скачиваем через быстрый системный curl.exe (встроен в Windows 10/11) с фоллбэком на PowerShell
where curl >nul 2>&1
if !errorlevel! equ 0 (
    curl -L --progress-bar "%INSTALLER_URL%" -o "%INSTALLER_PATH%"
) else (
    powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '%INSTALLER_URL%' -OutFile '%INSTALLER_PATH%'"
)

if not exist "%INSTALLER_PATH%" (
    echo.
    echo   %C_RED%[x] КРИТИЧЕСКАЯ ОШИБКА: Не удалось скачать установщик Python.%C_RESET%
    echo   %C_GRAY%    Проверьте подключение к сети Интернет и повторите попытку.%C_RESET%
    pause
    exit /b 1
)

echo   %C_CYAN%[»] Развертывание Python (Silent Mode + PATH + Pip + Tcl/Tk)...%C_RESET%
start /wait "" "%INSTALLER_PATH%" /quiet InstallAllUsers=0 PrependPath=1 Include_pip=1 Include_tcltk=1 AssociateFiles=1 Shortcuts=0

del /f /q "%INSTALLER_PATH%" >nul 2>&1

set "PY_DIR=%LOCALAPPDATA%\Programs\Python\Python311"
set "PATH=!PY_DIR!;!PY_DIR!\Scripts;!PATH!"
set "PY_CMD=!PY_DIR!\python.exe"
set "PYW_CMD=!PY_DIR!\pythonw.exe"

if not exist "!PY_CMD!" (
    echo   %C_RED%[x] Установка завершена, но требуется перезапуск окна терминала.%C_RESET%
    pause
    exit /b 1
)

echo   %C_GREEN%[✓] Python 3.11.9 успешно интегрирован в систему!%C_RESET%

:: ============================================================================
:: ЭТАП 2. ПРОВЕРКА И ДОУСТАНОВКА БИБЛИОТЕК SENTINEL OS
:: ============================================================================
:CHECK_DEPS
echo.
echo %C_BLUE%[2/3]%C_RESET% %C_WHITE%Аудит и синхронизация зависимостей Sentinel OS...%C_RESET%

:: Поштучная умная проверка каждого пакета (не тратит время, если уже установлено)
call :VERIFY_PKG "psutil"  "psutil"  "Телеметрия CPU/RAM и мониторинг процессов"
call :VERIFY_PKG "PIL"     "Pillow"  "Генерация векторных иконок и графики"
call :VERIFY_PKG "pystray" "pystray" "Интеграция в системный трей Windows"
call :VERIFY_PKG "pynput"  "pynput"  "Глобальные хуки клавиатуры и мыши"

echo.
echo %C_BLUE%[3/3]%C_RESET% %C_WHITE%Проверка модулей Sentinel OS в рабочей директории...%C_RESET%

set "SORTER_FILE=file_sorter.pyw"
set "DIMMER_FILE=sentinel_dimmer.pyw"
if not exist "!DIMMER_FILE!" if exist "sentinel_focus_shade.pyw" set "DIMMER_FILE=sentinel_focus_shade.pyw"

if exist "!SORTER_FILE!" (
    echo   %C_GREEN%[✓] Модуль сортировки и защиты:%C_RESET% %C_CYAN%!SORTER_FILE!%C_RESET% %C_GREEN%[ГОТОВ]%C_RESET%
) else (
    echo   %C_YELLOW%[!] Модуль сортировки (!SORTER_FILE!) не найден в этой папке.%C_RESET%
)

if exist "!DIMMER_FILE!" (
    echo   %C_GREEN%[✓] Модуль матрицы мониторов:%C_RESET%   %C_CYAN%!DIMMER_FILE!%C_RESET% %C_GREEN%[ГОТОВ]%C_RESET%
) else (
    echo   %C_YELLOW%[!] Модуль затемнения (!DIMMER_FILE!) не найден в этой папке.%C_RESET%
)

:: ============================================================================
:: ОПЕРАТИВНОЕ МЕНЮ УПРАВЛЕНИЯ (SENTINEL LAUNCHER DECK)
:: ============================================================================
:LAUNCHER_MENU
echo.
echo %C_CYAN%╔════════════════════════════════════════════════════════════════════════════════════════╗%C_RESET%
echo %C_CYAN%║%C_RESET%  %C_BOLD%%C_GREEN%✓ ОКРУЖЕНИЕ СИНХРОНИЗИРОВАНО.%C_RESET% %C_WHITE%Выберите операцию, Operator:%C_RESET%                            %C_CYAN%║%C_RESET%
echo %C_CYAN%╠════════════════════════════════════════════════════════════════════════════════════════╣%C_RESET%
echo %C_CYAN%║%C_RESET%  %C_YELLOW%[1]%C_RESET% 🚀 Запустить %C_CYAN% ОБА МОДУЛЯ %C_RESET% (File Sorter + Focus Shade Matrix)                     %C_CYAN%║%C_RESET%
echo %C_CYAN%║%C_RESET%  %C_YELLOW%[2]%C_RESET% 📂 Запустить только %C_GREEN%Sentinel File Sorter ^& AV%C_RESET% (!SORTER_FILE!)                  %C_CYAN%║%C_RESET%
echo %C_CYAN%║%C_RESET%  %C_YELLOW%[3]%C_RESET% 🖥  Запустить только %C_GREEN%Sentinel Focus Shade Matrix%C_RESET% (!DIMMER_FILE!)               %C_CYAN%║%C_RESET%
echo %C_CYAN%║%C_RESET%  %C_YELLOW%[4]%C_RESET% 🔗 Создать ярлыки быстрого запуска на Рабочем столе                               %C_CYAN%║%C_RESET%
echo %C_CYAN%║%C_RESET%  %C_YELLOW%[5]%C_RESET% 🔄 Принудительно обновить все библиотеки через PIP                                %C_CYAN%║%C_RESET%
echo %C_CYAN%║%C_RESET%  %C_YELLOW%[6]%C_RESET% 🛑 Завершить все фоновые процессы Sentinel (Kill pythonw.exe)                     %C_CYAN%║%C_RESET%
echo %C_CYAN%║%C_RESET%  %C_GRAY%[0] Выход из лаунчера%C_RESET%                                                                 %C_CYAN%║%C_RESET%
echo %C_CYAN%╚════════════════════════════════════════════════════════════════════════════════════════╝%C_RESET%
echo.
set /p "USER_CHOICE=%C_GREEN%Operator@Sentinel:~$ %C_RESET%"

if "!USER_CHOICE!"=="1" (
    call :LAUNCH_SCRIPT "!SORTER_FILE!"
    call :LAUNCH_SCRIPT "!DIMMER_FILE!"
    echo   %C_PURPLE%★ Оба комплекса Sentinel OS запущены в фоновом режиме. Закрытие через 2 сек...%C_RESET%
    timeout /t 2 >nul
    exit /b 0
)
if "!USER_CHOICE!"=="2" (
    call :LAUNCH_SCRIPT "!SORTER_FILE!"
    goto :LAUNCHER_MENU
)
if "!USER_CHOICE!"=="3" (
    call :LAUNCH_SCRIPT "!DIMMER_FILE!"
    goto :LAUNCHER_MENU
)
if "!USER_CHOICE!"=="4" (
    call :CREATE_SHORTCUTS
    goto :LAUNCHER_MENU
)
if "!USER_CHOICE!"=="5" (
    echo.
    echo   %C_CYAN%[»] Обновление pip и всех пакетов до последних релизов...%C_RESET%
    "!PY_CMD!" -m pip install --upgrade pip psutil pillow pystray pynput
    echo   %C_GREEN%[✓] Все пакеты обновлены!%C_RESET%
    goto :LAUNCHER_MENU
)
if "!USER_CHOICE!"=="6" (
    echo.
    taskkill /f /im pythonw.exe >nul 2>&1
    if !errorlevel! equ 0 (
        echo   %C_YELLOW%[!] Все фоновые процессы pythonw.exe успешно остановлены.%C_RESET%
    ) else (
        echo   %C_GRAY%[i] Активных фоновых процессов pythonw.exe не обнаружено.%C_RESET%
    )
    goto :LAUNCHER_MENU
)
if "!USER_CHOICE!"=="0" exit /b 0
if "!USER_CHOICE!"=="" exit /b 0

echo   %C_RED%[!] Неизвестная команда. Введите цифру от 0 до 6.%C_RESET%
goto :LAUNCHER_MENU


:: ============================================================================
:: ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
:: ============================================================================

:VERIFY_PKG
set "MOD_IMPORT=%~1"
set "PIP_NAME=%~2"
set "MOD_DESC=%~3"

"!PY_CMD!" -c "import !MOD_IMPORT!" >nul 2>&1
if !errorlevel! equ 0 (
    echo   %C_GREEN%[✓] Пакет !PIP_NAME!:%C_RESET% установлен %C_GRAY%(!MOD_DESC!)%C_RESET%
) else (
    echo   %C_YELLOW%[»] Установка пакета !PIP_NAME! (!MOD_DESC!)...%C_RESET%
    "!PY_CMD!" -m pip install !PIP_NAME! --quiet --disable-pip-version-check
    if !errorlevel! equ 0 (
        echo   %C_GREEN%[✓] Пакет !PIP_NAME! успешно установлен!%C_RESET%
    ) else (
        echo   %C_RED%[x] Ошибка установки пакета !PIP_NAME!!%C_RESET%
    )
)
exit /b 0


:LAUNCH_SCRIPT
set "TARGET_PYW=%~1"
if not exist "!TARGET_PYW!" (
    echo   %C_RED%[x] Файл !TARGET_PYW! не найден в папке %CD%!%C_RESET%
    exit /b 1
)
if exist "!PYW_CMD!" (
    start "" "!PYW_CMD!" "%CD%\!TARGET_PYW!"
) else (
    start "" pythonw "%CD%\!TARGET_PYW!"
)
echo   %C_GREEN%[✓] Модуль !TARGET_PYW! запущен.%C_RESET%
exit /b 0


:CREATE_SHORTCUTS
echo.
echo   %C_CYAN%[»] Генерация ярлыков на Рабочем столе...%C_RESET%
if exist "!SORTER_FILE!" (
    powershell -NoProfile -Command "$s=(New-Object -COM WScript.Shell).CreateShortcut([Environment]::GetFolderPath('Desktop')+'\Sentinel File Sorter.lnk'); $s.TargetPath='!PYW_CMD!'; $s.Arguments='\"%CD%\!SORTER_FILE!\"'; $s.WorkingDirectory='%CD%'; $s.IconLocation='shell32.dll,43'; $s.Save()"
    echo   %C_GREEN%[✓] Создан ярлык: «Sentinel File Sorter»%C_RESET%
)
if exist "!DIMMER_FILE!" (
    powershell -NoProfile -Command "$s=(New-Object -COM WScript.Shell).CreateShortcut([Environment]::GetFolderPath('Desktop')+'\Sentinel Focus Matrix.lnk'); $s.TargetPath='!PYW_CMD!'; $s.Arguments='\"%CD%\!DIMMER_FILE!\"'; $s.WorkingDirectory='%CD%'; $s.IconLocation='shell32.dll,21'; $s.Save()"
    echo   %C_GREEN%[✓] Создан ярлык: «Sentinel Focus Matrix»%C_RESET%
)
exit /b 0
