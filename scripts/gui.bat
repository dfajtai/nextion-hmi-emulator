@echo off
rem Opens the generator window (PySide6). Optional argument: a .HMI file to preselect (drag it onto this file).
rem Looks for PySide6 in this order and only installs when it finds none:
rem   1. the project's private venv   2. the system Python (py -3)   3. install into the private venv
setlocal
set "ROOT=%~dp0.."
if not defined NEXTION_VENV set "NEXTION_VENV=%ROOT%\.venv"
set "PYTHONPATH=%ROOT%\code;%PYTHONPATH%"

if exist "%NEXTION_VENV%\Scripts\python.exe" (
  "%NEXTION_VENV%\Scripts\python.exe" -c "import PySide6.QtUiTools" >nul 2>&1
  if not errorlevel 1 (
    start "" "%NEXTION_VENV%\Scripts\pythonw.exe" -m nextion_parser gui %*
    exit /b 0
  )
)
py -3 -c "import PySide6.QtUiTools" >nul 2>&1
if not errorlevel 1 (
  echo using PySide6 from the system Python
  start "" pyw -3 -m nextion_parser gui %*
  exit /b 0
)
echo PySide6 (about 80 MB) is not installed.
choice /m "Install it into the project's private venv (%NEXTION_VENV%)"
if errorlevel 2 (echo Aborted. Alternative: pip install PySide6-Essentials & pause & exit /b 1)
call "%~dp0setup.bat" gui || (echo Installation failed - no internet? Install manually: pip install PySide6-Essentials & pause & exit /b 1)
start "" "%NEXTION_VENV%\Scripts\pythonw.exe" -m nextion_parser gui %*
