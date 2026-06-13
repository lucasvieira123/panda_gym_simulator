$python = "C:\Users\lucas_alves\AppData\Local\Programs\Python\Python313\python.exe"
$root   = $PSScriptRoot

Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\managing'; & '$python' main.py"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\manager';  & '$python' main.py"
