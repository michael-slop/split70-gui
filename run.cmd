@echo off
rem Launch the Split70 Configurator without a console window.
setlocal
cd /d "%~dp0"
where pythonw >nul 2>&1 && (start "" pythonw app.py %*) || (python app.py %*)
