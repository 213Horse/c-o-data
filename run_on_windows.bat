@echo off
setlocal
echo ==========================================
echo    Cai dat va Chay ISBN Scraper
echo ==========================================

:: Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [LOI] Khong tim thay Python tren may tinh nay!
    echo ------------------------------------------
    echo Ban can cai dat Python de chay tool nay:
    echo 1. Tai Python tai: https://www.python.org/downloads/
    echo 2. Khi cai dat, bat buoc phai tich chon "Add Python to PATH"
    echo 3. Sau khi cai xong, hay mo lai file nay.
    echo ------------------------------------------
    pause
    exit /b
)

:: Create virtual environment if it doesn't exist
if not exist venv (
    echo Dang tao moi truong ao (virtual environment)...
    python -m venv venv
)

:: Activate virtual environment
echo Dang kich hoat moi truong ao...
call venv\Scripts\activate

:: Install/Update dependencies
echo Dang cai dat/cap nhat cac thu vien can thiet...
python -m pip install --upgrade pip
pip install -r requirements.txt

:: Run the GUI application
echo ------------------------------------------
echo Dang khoi dong ung dung...
python gui_cao.py

:: Keep window open if app closes
echo ------------------------------------------
echo Ung dung da dung lai.
pause
deactivate
