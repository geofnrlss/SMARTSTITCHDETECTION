@echo off
REM 1) pindah ke folder script
cd /d "%~dp0"

REM 2) jalankan login.pyw via pythonw tanpa console
start "" "C:\Users\PETROKIMIA GRESIK\AppData\Local\Programs\Python\Python310\pythonw.exe" login.pyw

REM 3) langsung exit batch, supaya konsol tidak nempel
exit
