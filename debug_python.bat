@echo off
setlocal
echo ==========================================
echo    Kiem tra moi truong Python
echo ==========================================

echo [1] Kiem tra lenh 'python':
where python
python --version

echo.
echo [2] Kiem tra lenh 'python3':
where python3
python3 --version

echo.
echo [3] Kiem tra lenh 'py' (Python Launcher):
where py
py -3 --version

echo.
echo ------------------------------------------
echo Neu tat ca tren deu bao "Could not find" hoac "not recognized",
echo thi ban CHUA cai dat Python hoac CHUA tich vao "Add Python to PATH".
echo.
echo Vui long:
echo 1. Di toi: https://www.python.org/downloads/
echo 2. Tai ban moi nhat.
echo 3. Khi chay file cai, HAY TICH VAO O: [Add Python to PATH]
echo ------------------------------------------
pause
