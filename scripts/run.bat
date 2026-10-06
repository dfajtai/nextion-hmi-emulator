@echo off
rem Runs nextion_parser (Windows):  scripts\run.bat all path\to\FILE.HMI   |   scripts\run.bat --test
setlocal
set "ROOT=%~dp0.."
if not defined NEXTION_VENV set "NEXTION_VENV=%ROOT%\.venv"
call "%~dp0setup.bat" >nul || exit /b 1
set "PYTHONPATH=%ROOT%\code;%PYTHONPATH%"
if "%~1"=="--test" (
  cd /d "%ROOT%\code" && "%NEXTION_VENV%\Scripts\python.exe" -m pytest -q tests
  exit /b %errorlevel%
)
"%NEXTION_VENV%\Scripts\python.exe" -m nextion_parser %*
