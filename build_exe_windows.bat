@echo off
setlocal
echo ==========================================
echo    Dong goi thanh file thuc thi (.exe)
echo ==========================================

:: Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python chua duoc cai dat.
    echo Vui long cai dat Python truoc khi build.
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

:: Install required libraries including pyinstaller
echo Dang cai dat thu vien va pyinstaller...
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

:: Build the .exe
echo ------------------------------------------
echo Dang tien hanh dong goi. Qua trinh nay co the mat vai phut...
pyinstaller --noconfirm --onedir --windowed --add-data "cao.py;." --hidden-import lxml --hidden-import openpyxl --collect-all curl_cffi gui_cao.py

echo ------------------------------------------
echo Qua trinh dong goi hoan tat!
echo File chay cua ban (gui_cao.exe) nam trong thu muc:
echo dist\gui_cao\gui_cao.exe
echo Ban co the copy nguyen thu muc "gui_cao" ra cho khac de su dung ma khong can cai Python.
pause
deactivate
