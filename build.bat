@echo off
rem ==============================================================================
rem Vihara - Single-Command Standalone Packaging and Installer Pipeline
rem Builds:
rem   1. PyInstaller onedir distribution: dist\vihara\
rem   2. Inno Setup 6 standalone installer: dist\installers\Vihara-Setup-x64.exe
rem ==============================================================================
setlocal enabledelayedexpansion

echo ==============================================================================
echo   Vihara Desktop Mindfulness Mirror - Build ^& Packaging Pipeline
echo ==============================================================================

rem Step 1: Verify Python Environment
echo [1/4] Checking Python environment...
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python was not found on PATH. Please install Python 3.10+ and add it to PATH.
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version') do set PYTHON_VER=%%i
echo       Detected: !PYTHON_VER!

rem Step 2: Verify PyInstaller
echo [2/4] Checking PyInstaller build tool...
python -c "import PyInstaller" >nul 2>&1
if !ERRORLEVEL! NEQ 0 (
    echo       PyInstaller not detected in current environment.
    echo       Installing PyInstaller...
    python -m pip install pyinstaller
    if !ERRORLEVEL! NEQ 0 (
        echo [ERROR] Failed to install PyInstaller. Run: pip install pyinstaller
        exit /b !ERRORLEVEL!
    )
)
for /f "tokens=*" %%i in ('python -m PyInstaller --version 2^>nul') do set PYINSTALLER_VER=%%i
echo       Detected PyInstaller !PYINSTALLER_VER!

rem Step 3: Run PyInstaller Onedir Compilation
echo [3/4] Compiling Vihara standalone distribution (onedir mode)...
if not exist "packaging\windows\vihara.spec" (
    echo [ERROR] Spec file not found: packaging\windows\vihara.spec
    exit /b 1
)

python -m PyInstaller --noconfirm --distpath dist --workpath build packaging\windows\vihara.spec
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] PyInstaller compilation failed with exit code %ERRORLEVEL%.
    exit /b %ERRORLEVEL%
)

if not exist "dist\vihara\vihara.exe" (
    echo [ERROR] Expected binary not found: dist\vihara\vihara.exe
    exit /b 1
)
echo       PyInstaller build successful: dist\vihara\

rem Step 4: Locate and Run Inno Setup Compiler (ISCC)
echo [4/4] Locating Inno Setup 6 compiler...
set ISCC_EXE=

where ISCC.exe >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    for /f "tokens=*" %%i in ('where ISCC.exe') do set "ISCC_EXE=%%i"
)

if "!ISCC_EXE!"=="" (
    if exist "!ProgramFiles(x86)!\Inno Setup 6\ISCC.exe" set "ISCC_EXE=!ProgramFiles(x86)!\Inno Setup 6\ISCC.exe"
    if exist "!ProgramFiles!\Inno Setup 6\ISCC.exe" set "ISCC_EXE=!ProgramFiles!\Inno Setup 6\ISCC.exe"
    if exist "!LOCALAPPDATA!\Programs\Inno Setup 6\ISCC.exe" set "ISCC_EXE=!LOCALAPPDATA!\Programs\Inno Setup 6\ISCC.exe"
)

if not "!ISCC_EXE!"=="" (
    echo       Found Inno Setup Compiler: !ISCC_EXE!
    echo       Compiling Windows Installer (dist\installers\Vihara-Setup-x64.exe)...
    if not exist "dist\installers" mkdir "dist\installers"
    "!ISCC_EXE!" "packaging\windows\installer.iss"
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Inno Setup compilation failed with exit code %ERRORLEVEL%.
        exit /b %ERRORLEVEL%
    )
    echo       Installer build successful: dist\installers\Vihara-Setup-x64.exe
) else (
    echo       [NOTICE] Inno Setup 6 (ISCC.exe) not found on PATH or default install locations.
    echo       Standalone distribution is ready at: dist\vihara\
    echo       To generate Vihara-Setup-x64.exe, install Inno Setup 6:
    echo         winget install JRSoftware.InnoSetup
    echo       or download from: https://jrsoftware.org/isdl.php
)

echo ==============================================================================
echo   Build Pipeline Complete!
echo   Standalone Application: dist\vihara\vihara.exe
if exist "dist\installers\Vihara-Setup-x64.exe" (
    echo   Standalone Installer:   dist\installers\Vihara-Setup-x64.exe
)
echo ==============================================================================
exit /b 0
