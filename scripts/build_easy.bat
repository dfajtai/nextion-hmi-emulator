@echo off
rem Builds dist\nextion-generator.pyz (single-file easy generator).
setlocal
set "ROOT=%~dp0.."
set "STAGE=%TEMP%\nxgen_stage"
if exist "%STAGE%" rmdir /s /q "%STAGE%"
xcopy /e /i /q "%ROOT%\code\nextion_parser" "%STAGE%\nextion_parser" >nul
if not exist "%ROOT%\dist" mkdir "%ROOT%\dist"
py -3 -m zipapp "%STAGE%" -o "%ROOT%\dist\nextion-generator.pyz" -m "nextion_parser.easy:run" || python -m zipapp "%STAGE%" -o "%ROOT%\dist\nextion-generator.pyz" -m "nextion_parser.easy:run"
rmdir /s /q "%STAGE%"
echo built: %ROOT%\dist\nextion-generator.pyz
