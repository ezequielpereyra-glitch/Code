@echo off
chcp 65001 >nul
title ServiceDesk - servidor (no cerrar esta ventana)
set DIR=%USERPROFILE%\ServiceDesk
cd /d "%DIR%" || (echo No existe %DIR%. Ejecuta instalar.bat primero. & pause & exit /b 1)
set PY=python
where python >nul 2>&1 || set PY=py
if not exist .tmp mkdir .tmp
echo.
echo ServiceDesk corriendo. Abrelo en http://localhost:8000
echo Desde otras PCs de la red usa la IP de esta maquina, por ejemplo http://192.168.1.50:8000
echo.
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do echo   Esta PC: http://%%a:8000
echo.
echo Cierra esta ventana para detenerlo.
start "" http://localhost:8000
%PY% -m uvicorn execution.servicedesk.app:app --host 0.0.0.0 --port 8000
pause
