@echo off
chcp 65001 >nul
title Sentinel OS :: Python Environment Bootstrap
color 0b

echo ========================================================
echo   SENTINEL OS :: ПРОВЕРКА И НАСТРОЙКА ОКРУЖЕНИЯ PYTHON
echo ========================================================
echo.

:: 1. Проверка наличия Python
python --version >nul 2>&1
if %errorlevel% neq 0 goto :INSTALL_PYTHON

for /f "tokens=2 delims= " %%i in ('python --version 2^>^&1') do set PY_VER=%%i
echo [+] Найден установленный Python: %PY_VER%

:: Проверка мажорной версии (должна быть 3)
for /f "tokens=1,2 delims=." %%a in ("%PY_VER%") do (
    set PY_MAJOR=%%a
    set PY_MINOR=%%b
)

if %PY_MAJOR% lss 3 goto :INSTALL_PYTHON
if %PY_MAJOR% equ 3 if %PY_MINOR% lss 10 goto :INSTALL_PYTHON

echo [✓] Версия Python актуальна (>= 3.10).
goto :CHECK_DEPS

:INSTALL_PYTHON
echo [!] Подходящий Python не обнаружен в PATH.
echo [>] Начинается автоматическая загрузка Python 3.11 (64-bit)...

set INSTALLER_URL=https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe
set INSTALLER_PATH=%temp%\python_setup.exe

powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object System.Net.WebClient).DownloadFile('%INSTALLER_URL%', '%INSTALLER_PATH%')"

if not exist "%INSTALLER_PATH%" (
    color 0c
    echo [x] Ошибка загрузки установщика. Проверьте интернет-соединение.
    pause
    exit /b
)

echo [>] Установка Python в тихом режиме с добавлением в PATH...
start /wait "" "%INSTALLER_PATH%" /quiet InstallAllUsers=0 PrependPath=1 Include_pip=1 Include_tcltk=1 AssociateFiles=1 Shortcuts=1

del /f /q "%INSTALLER_PATH%" >nul 2>&1

:: Обновление переменных среды текущей сессии
set "PATH=%LOCALAPPDATA%\Programs\Python\Python311;%LOCALAPPDATA%\Programs\Python\Python311\Scripts;%PATH%"

python --version >nul 2>&1
if %errorlevel% neq 0 (
    color 0c
    echo [!] Установка завершена, но требуется перезапуск сессии или командной строки.
    pause
    exit /b
)

echo [✓] Python успешно установлен и интегрирован в систему!

:CHECK_DEPS
echo.
echo ========================================================
echo   ПРОВЕРКА И ДОУСТАНОВКА ЗАВИСИМОСТЕЙ
echo ========================================================
echo.
echo [>] Обновление pip...
python -m pip install --upgrade pip --quiet

echo [>] Установка пакетов для Sentinel OS (psutil, pillow, pystray, pynput)...
python -m pip install psutil pillow pystray pynput --quiet

echo.
echo ========================================================
echo [✓] ВСЁ ГОТОВО! Окружение настроено под Sentinel OS.
echo Теперь можно запускать file_sorter.pyw и sentinel_dimmer.pyw.
echo ========================================================
echo.
pause