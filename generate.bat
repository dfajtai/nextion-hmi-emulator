@echo off
rem Put your .HMI file(s) next to this file and double-click it, or name them:  generate.bat a.HMI b.HMI
rem Everything is generated into output\<name>\ and the launcher page opens. First run creates the Python environment by itself.
rem The window stays open until a key is pressed, also after an error.
set "NX_NO_PAUSE=1"
if "%~1"=="" cd /d "%~dp0"
call "%~dp0scripts\run.bat" %*
set "RC=%errorlevel%"
if not "%RC%"=="0" if not "%RC%"=="4" (echo. & echo Something went wrong ^(exit code %RC%^) - see the messages above.)
echo.
pause
exit /b %RC%
