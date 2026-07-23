@echo off
set "ROOT=%~dp0"

@REM start "dashboard" cmd /k pushd "%ROOT%" ^&^& call ".venv\Scripts\activate.bat" ^&^& streamlit run 0-dashboard\app.py

start "managing"  cmd /k pushd "%ROOT%2-managing" ^&^& call "%ROOT%.venv\Scripts\activate.bat" ^&^& python main.py
start "manager"   cmd /k pushd "%ROOT%1-manager"  ^&^& call "%ROOT%.venv\Scripts\activate.bat" ^&^& python main.py
