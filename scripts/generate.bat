@echo off
rem Drag a .HMI file onto this file: generates everything into output\<name>\ and opens the launcher page.
setlocal
if "%~1"=="" (echo Drag a .HMI file onto this file. & pause & exit /b 1)
call "%~dp0run.bat" all "%~1"
if errorlevel 1 (pause & exit /b 1)
start "" "%~dp0..\output\%~n1\index.html"
pause
