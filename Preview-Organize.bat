@echo off
setlocal EnableDelayedExpansion
set "SCRIPT=%~dp0organize_files.py"

if "%~1"=="" (
  set /p TARGET=Folder to preview: 
) else (
  set "TARGET=%~1"
)
set "TARGET=%TARGET:"=%"

:MENU
cls
echo FileOrganizer - Preview mode
echo.
echo Target folder:
echo !TARGET!
echo.
echo Choose organize mode:
echo 1. Smart - detailed file format
echo 2. Date only
echo 3. File type only
echo 4. Name initial - Korean/English initial folders
echo 5. Original return - collect files back here
echo 6. Change target folder
echo 0. Exit
echo.
set /p MODE_CHOICE=Choose 0-6, or press Enter for Smart: 

if "!MODE_CHOICE!"=="0" exit /b 0
if "!MODE_CHOICE!"=="6" (
  echo.
  set /p TARGET=Folder to preview: 
  set "TARGET=!TARGET:"=!"
  goto MENU
)

set "MODE=smart"
if "!MODE_CHOICE!"=="2" set "MODE=date"
if "!MODE_CHOICE!"=="3" set "MODE=type"
if "!MODE_CHOICE!"=="4" set "MODE=initial"
if "!MODE_CHOICE!"=="5" set "MODE=name"

echo.
echo Selected mode: !MODE!
py "%SCRIPT%" organize "!TARGET!" --recursive --rules "%~dp0rules.example.json" --mode "!MODE!"
echo.
echo Done. Choose another preview, change folder, or exit.
set /p CONTINUE=Press Enter to return to the menu...
goto MENU
