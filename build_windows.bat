@echo off
REM ---------------------------------------------------------------------
REM build_windows.bat
REM
REM Installs dependencies and builds a standalone Windows .exe for the
REM PDF Password Tester using PyInstaller.
REM
REM Run this from a Command Prompt inside the pdf_password_tester folder.
REM ---------------------------------------------------------------------

echo Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo Failed to install requirements.
    pause
    exit /b 1
)

echo Installing PyInstaller...
pip install pyinstaller
if errorlevel 1 (
    echo Failed to install PyInstaller.
    pause
    exit /b 1
)

echo Building executable...
pyinstaller --onefile --windowed --name "PDFPasswordTester" main.py
if errorlevel 1 (
    echo Build failed.
    pause
    exit /b 1
)

echo.
echo Build complete. The executable is in the "dist" folder:
echo   dist\PDFPasswordTester.exe
pause
