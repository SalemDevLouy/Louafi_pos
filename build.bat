@echo off
setlocal

set APP_NAME=LouafiPOS
set ENTRY=main.py
set DIST=dist
set ICON=assets\logo.ico

echo Building %APP_NAME%...

pyinstaller ^
    --name "%APP_NAME%" ^
    --onedir ^
    --windowed ^
    --icon "%ICON%" ^
    --add-data "config.ini;." ^
    --add-data "styles.qss;." ^
    --add-data "lang;lang" ^
    --add-data "assets;assets" ^
    --hidden-import "pyzbar.pyzbar" ^
    --hidden-import "cv2" ^
    --hidden-import "reportlab" ^
    --hidden-import "arabic_reshaper" ^
    --hidden-import "bidi" ^
    --hidden-import "openpyxl" ^
    --hidden-import "matplotlib" ^
    --clean ^
    "%ENTRY%"

if %ERRORLEVEL% NEQ 0 (
    echo Build failed!
    pause
    exit /b 1
)

echo.
echo Build complete: %DIST%\%APP_NAME%\
echo.
echo Running NSIS installer build...
makensis installer\setup.nsi

echo Done.
pause
