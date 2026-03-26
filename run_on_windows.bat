@echo off
setlocal
echo ==========================================
echo    Cai dat va Chay ISBN Scraper
echo ==========================================

:: Check if Python is installed (check python, then python3, then py)
set PYTHON_CMD=python
%PYTHON_CMD% --version >nul 2>&1
if %errorlevel% neq 0 (
    set PYTHON_CMD=python3
    %PYTHON_CMD% --version >nul 2>&1
)
if %errorlevel% neq 0 (
    set PYTHON_CMD=py -3
    %PYTHON_CMD% --version >nul 2>&1
)

if %errorlevel% neq 0 (
    echo [LOI] Khong tim thay Python tren may tinh nay!
    echo ------------------------------------------
    echo Ban can cai dat Python de chay tool nay:
    echo 1. Tai Python tai: https://www.python.org/downloads/
    echo 2. Khi cai dat, BAT BUOC phai tich chon "Add Python to PATH"
    echo 3. Sau khi cai xong, hay mo lai file nay.
    echo ------------------------------------------
    pause
    exit /b
)

:: Create virtual environment if it doesn't exist or is invalid
if exist venv (
    if not exist venv\Scripts\activate.bat (
        echo [CANH BAO] Thu muc venv hien tai khong tuong thich voi Windows.
        echo Dang xoa va tao lai...
        rmdir /s /q venv
    )
)

if not exist venv (
    echo Dang tao moi truong ao (virtual environment)...
    %PYTHON_CMD% -m venv venv
    if %errorlevel% neq 0 (
        echo [LOI] Khong the tao virtual environment.
        pause
        exit /b
    )
)

:: Activate virtual environment
echo Dang kich hoat moi truong ao...
call venv\Scripts\activate
if %errorlevel% neq 0 (
    echo [LOI] Khong the kich hoat virtual environment.
    pause
    exit /b
)

:: Install/Update dependencies
echo Dang cai dat/cap nhat cac thu vien can thiet...
python -m pip install --upgrade pip
pip install -r requirements.txt

:: Run the GUI application
echo ------------------------------------------
echo Dang khoi dong ung dung...
python gui_cao.py
if %errorlevel% neq 0 (
    echo [LOI] Ung dung gap loi khi dang chay.
)

:: Keep window open if app closes
echo ------------------------------------------
echo Ung dung da dung lai.
pause
deactivate
