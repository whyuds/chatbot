@echo off
REM Check Python installation
python --version >nul 2>&1 || (
    echo Python not installed or not in PATH
    pause
    exit /b 1
)

REM Activate virtual environment
call .\venv\Scripts\activate

REM Check dependencies
pip freeze | findstr "fastapi uvicorn sqlalchemy" >nul || (
    echo Installing dependencies...
    pip install -r requirements.txt
)

REM Initialize database
python init_db.py

REM Start backend server
start "Backend Server" python -m uvicorn main:app --host 0.0.0.0 --port 8000

REM Start frontend server
cd frontend
start "Frontend Server" python -m http.server 8080

REM Open browser after 3 seconds
timeout 3 >nul
start http://localhost:8080/frontend/

echo Servers started successfully!
pause