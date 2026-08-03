@echo off
set "ROOT=%~dp0"

netstat -ano | findstr ":8501" | findstr "LISTENING" > NUL 2>&1
if %errorlevel% neq 0 (
    start "console" cmd /k pushd "%ROOT%" ^&^& call ".venv\Scripts\activate.bat" ^&^& streamlit run 0-console\app.py
) else (
    echo [run] Streamlit ja esta a correr em http://localhost:8501
)

netstat -ano | findstr ":8502" | findstr "LISTENING" > NUL 2>&1
if %errorlevel% neq 0 (
    start "dejavu-console" cmd /k pushd "%ROOT%" ^&^& call ".venv\Scripts\activate.bat" ^&^& streamlit run 4-dejavu-console\app.py --server.port 8502
) else (
    echo [run] DejaVu Console ja esta a correr em http://localhost:8502
)
