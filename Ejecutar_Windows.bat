@echo off
setlocal
cd /d "%~dp0"

echo ==========================================
echo   Evaluador de Agroquimicos - Windows
echo ==========================================
echo.

set "PYTHON_CMD="

where py >nul 2>&1
if %errorlevel%==0 set "PYTHON_CMD=py"

if not defined PYTHON_CMD (
    where python >nul 2>&1
    if %errorlevel%==0 set "PYTHON_CMD=python"
)

if not defined PYTHON_CMD (
    echo ERROR: No se encontro Python en este equipo.
    echo.
    echo Instala Python 3 desde https://www.python.org/downloads/
    echo Durante la instalacion marca "Add Python to PATH".
    echo Despues vuelve a ejecutar este archivo.
    echo.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo Creando entorno virtual local...
    %PYTHON_CMD% -m venv .venv
    if errorlevel 1 (
        echo.
        echo ERROR: No fue posible crear el entorno virtual.
        pause
        exit /b 1
    )
)

set "VENV_PY=.venv\Scripts\python.exe"

"%VENV_PY%" -c "import streamlit, fitz" >nul 2>&1
if errorlevel 1 (
    echo Instalando dependencias necesarias...
    "%VENV_PY%" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo ERROR: No fue posible instalar las dependencias.
        echo Comprueba tu conexion a Internet y vuelve a intentarlo.
        pause
        exit /b 1
    )
)

echo.
echo Iniciando la aplicacion...
echo La interfaz se abrira en tu navegador.
echo Para cerrar la aplicacion, cierra esta ventana o pulsa Ctrl+C.
echo.

"%VENV_PY%" -m streamlit run app.py

echo.
echo La aplicacion se ha detenido.
pause
