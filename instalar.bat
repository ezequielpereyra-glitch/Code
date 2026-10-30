@echo off
chcp 65001 >nul
setlocal
title ServiceDesk - Instalador
echo ============================================
echo   ServiceDesk - instalacion / actualizacion
echo ============================================
echo.

where python >nul 2>&1 || where py >nul 2>&1
if errorlevel 1 (
  echo [ERROR] No se encontro Python.
  echo Instalalo desde https://www.python.org/downloads/ marcando "Add Python to PATH" y vuelve a ejecutar este archivo.
  pause & exit /b 1
)
set PY=python
where python >nul 2>&1 || set PY=py

where git >nul 2>&1
if errorlevel 1 (
  echo [ERROR] No se encontro Git.
  echo Instalalo desde https://git-scm.com/download/win y vuelve a ejecutar este archivo.
  pause & exit /b 1
)

set REPO=https://github.com/ezequielpereyra-glitch/code
set RAMA=claude/blissful-babbage-n9nevc
set DIR=%USERPROFILE%\ServiceDesk

if exist "%DIR%\.git" (
  echo Actualizando el programa...
  git -C "%DIR%" pull --ff-only || (echo [ERROR] No se pudo actualizar. & pause & exit /b 1)
) else (
  echo Descargando el programa en %DIR% ...
  git clone -b %RAMA% %REPO% "%DIR%" || (echo [ERROR] No se pudo descargar. & pause & exit /b 1)
)

echo Instalando dependencias...
%PY% -m pip install --quiet --upgrade pip
%PY% -m pip install --quiet -r "%DIR%\requirements.txt" || (echo [ERROR] Fallo la instalacion de dependencias. & pause & exit /b 1)

copy /y "%DIR%\iniciar.bat" "%USERPROFILE%\Desktop\ServiceDesk.bat" >nul 2>&1
echo.
echo Listo. Se creo "ServiceDesk.bat" en tu Escritorio para arrancarlo en el futuro.
echo Arrancando ahora...
call "%DIR%\iniciar.bat"
