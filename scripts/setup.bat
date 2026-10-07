@echo off
rem One-time environment setup (Windows): private venv + requirements. run.bat calls this automatically.
setlocal
set "ROOT=%~dp0.."
if not defined NEXTION_VENV set "NEXTION_VENV=%ROOT%\.venv"
if not exist "%NEXTION_VENV%\Scripts\python.exe" (
  echo creating venv: %NEXTION_VENV%
  py -3 -m venv "%NEXTION_VENV%" || python -m venv "%NEXTION_VENV%" || (echo Python 3 not found & exit /b 1)
)
"%NEXTION_VENV%\Scripts\python.exe" -m pip install --quiet -r "%ROOT%\code\requirements.txt"
if /i "%~1"=="gui" "%NEXTION_VENV%\Scripts\python.exe" -m pip install --quiet -r "%ROOT%\code\requirements-gui.txt"
