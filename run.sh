#!/bin/bash
ROOT="$(cd "$(dirname "$0")" && pwd)"
PYTHON="/c/Users/lucas_alves/AppData/Local/Programs/Python/Python313/python.exe"

mintty -t "managing" bash -c "cd '$ROOT/managing' && '$PYTHON' main.py; read" &
mintty -t "manager"  bash -c "cd '$ROOT/manager'  && '$PYTHON' main.py; read" &
