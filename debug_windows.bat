@echo on
setlocal
echo ==========================================
echo    Kiem tra moi truong (FULL DEBUG - No Blocks)
echo ==========================================

:: 1. Kiem tra Python
echo [1/4] Dang kiem tra Python...
set PYTHON_CMD=python
python --version >nul 2>&1
if %errorlevel% equ 0 goto check_venv

set PYTHON_CMD=python3
python3 --version >nul 2>&1
if %errorlevel% equ 0 goto check_venv

set PYTHON_CMD=py -3
py -3 --version >nul 2>&1
if %errorlevel% equ 0 goto check_venv

echo [LOI] Khong tim thay Python!
pause
exit /b

:check_venv
echo Python is: %PYTHON_CMD%
%PYTHON_CMD% --version

echo.
echo [2/4] Dang kiem tra virtual environment (venv)...
if not exist venv goto create_venv
if exist venv\Scripts\activate.bat goto venv_ready

echo [CANH BAO] venv khong hop le hoac bi loi tren Windows. Dang xoa...
rmdir /s /q venv

:create_venv
if exist venv goto venv_ready
echo [INFO] Dang tao venv moi (Co the mat 10-20 giay)...
%PYTHON_CMD% -m venv venv
if %errorlevel% neq 0 goto venv_fail
echo [OK] Tao venv thanh cong.
goto venv_ready

:venv_fail
echo [LOI] Khong the tao venv!
pause
exit /b

:venv_ready
echo.
echo [3/4] Dang kich hoat venv va cai dat thu vien...
call venv\Scripts\activate
if %errorlevel% neq 0 goto act_fail

echo Dang cap nhat pip...
python -m pip install --upgrade pip

echo Dang cai dat requirements.txt (Co the mat vai phut)...
pip install -r requirements.txt
if %errorlevel% neq 0 goto req_fail
echo [OK] Cai dat thu vien thanh cong.
goto run_app

:act_fail
echo [LOI] Khong the kich hoat venv!
pause
exit /b

:req_fail
echo [LOI] Cai dat thu vien that bai! Hay kiem tra ket noi mang hoac loi do doan nay.
pause
exit /b

:run_app
echo.
echo [4/4] Dang thu chay gui_cao.py...
python gui_cao.py
if %errorlevel% neq 0 goto run_fail
echo ------------------------------------------
echo HOAN TAT KIEM TRA.
pause
exit /b

:run_fail
echo [LOI] Khong the chay script chinh!
pause
exit /b
