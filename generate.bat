@echo off
rem Put your .HMI file(s) next to this file and double-click it.
rem Everything is generated into output\<name>\ and the launcher page opens. First run creates the Python environment by itself.
cd /d "%~dp0"
call scripts\run.bat %*
if errorlevel 1 pause
