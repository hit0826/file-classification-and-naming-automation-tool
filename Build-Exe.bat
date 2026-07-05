@echo off
setlocal
cd /d "%~dp0"
py -m pip install pyinstaller
py -m PyInstaller --onefile --windowed --name FileOrganizer file_organizer_gui.py
if exist "dist\FileOrganizer.exe" copy /Y "dist\FileOrganizer.exe" "%~dp0FileOrganizer.exe" >nul
echo Build complete: %~dp0FileOrganizer.exe
pause
