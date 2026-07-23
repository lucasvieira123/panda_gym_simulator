@echo off
set "ROOT=%~dp0"

echo [run] A verificar se Streamlit esta a correr na porta 8501...
netstat -ano | findstr ":8501" | findstr "LISTENING" > NUL 2>&1
if %errorlevel% neq 0 (
    echo [run] Streamlit nao detectado. A iniciar dashboard...
    start "dashboard" cmd /k pushd "%ROOT%" ^&^& call ".venv\Scripts\activate.bat" ^&^& streamlit run 0-dashboard\app.py
    echo [run] Aguardando Streamlit carregar ^(10s^)...
    ping -n 11 127.0.0.1 > NUL
    echo [run] Streamlit pronto.
) else (
    echo [run] Streamlit ja esta a correr. A saltar dashboard.
)

echo [run] A iniciar managing...
start "managing"  cmd /k pushd "%ROOT%2-managing" ^&^& call "%ROOT%.venv\Scripts\activate.bat" ^&^& python main.py

echo [run] A iniciar manager...
start "manager"   cmd /k pushd "%ROOT%1-manager"  ^&^& call "%ROOT%.venv\Scripts\activate.bat" ^&^& python main.py

echo [run] Todos os processos iniciados.
