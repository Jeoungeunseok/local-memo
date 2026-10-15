@echo off
cd /d "%~dp0"
title StickyCalendar EXE Builder

echo ========================================================
echo   StickyCalendar EXE Build Process
echo ========================================================
echo.

where pyinstaller >nul 2>nul
if %errorlevel% neq 0 (
    if exist "C:\Users\%USERNAME%\old\anaconda3\Scripts\pyinstaller.exe" (
        set "PYI=C:\Users\%USERNAME%\old\anaconda3\Scripts\pyinstaller.exe"
    ) else if exist "C:\Users\%USERNAME%\anaconda3\Scripts\pyinstaller.exe" (
        set "PYI=C:\Users\%USERNAME%\anaconda3\Scripts\pyinstaller.exe"
    ) else (
        echo [ERROR] PyInstaller not found. Please run pip install pyinstaller.
        pause
        exit /b 1
    )
) else (
    set "PYI=pyinstaller"
)

set "LIB_BIN=C:\Users\%USERNAME%\old\anaconda3\Library\bin"
if not exist "%LIB_BIN%" (
    set "LIB_BIN=C:\Users\%USERNAME%\anaconda3\Library\bin"
)

echo [1/2] Building standalone executable with PyInstaller...
set "PATH=%LIB_BIN%;%PATH%"
"%PYI%" --noconsole --onefile --windowed --icon="app_icon.ico" --name="StickyCalendar" --paths="%LIB_BIN%" --add-binary="%LIB_BIN%\sqlite3.dll;." --add-binary="%LIB_BIN%\ffi.dll;." --clean sticky_calendar.py

if %errorlevel% equ 0 (
    echo.
    echo ========================================================
    echo   [SUCCESS] Build finished successfully!
    echo   Output file: dist\StickyCalendar.exe
    echo ========================================================
) else (
    echo.
    echo [ERROR] Build failed.
)

pause
