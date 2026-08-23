@echo off
cd /d C:\ai-caption-server\main\xiaozhi-server
:loop
"C:\Users\Administrator\AppData\Local\Programs\Python\Python311\python.exe" app.py >> "C:\ai-caption-server\main\xiaozhi-server\tmp\ai-caption-service.log" 2>&1
timeout /t 5 /nobreak >nul
goto loop
