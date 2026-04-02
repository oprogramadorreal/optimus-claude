@echo off
SETLOCAL

set PYTHON_ENV_DIR=%~dp0\.venv

REM Remove existing environment if it exists
if exist "%PYTHON_ENV_DIR%" (
    echo Removing existing Python virtual environment...
    rmdir /s /q "%PYTHON_ENV_DIR%"
)

REM Create a Python virtual environment
echo Creating Python virtual environment...
python -m venv %PYTHON_ENV_DIR%

IF ERRORLEVEL 1 (
    echo Failed to create virtual environment
    exit /b 1
)

REM Activate the virtual environment
echo Activating virtual environment...
CALL %PYTHON_ENV_DIR%\Scripts\activate

IF ERRORLEVEL 1 (
    echo Failed to activate virtual environment
    exit /b 1
)

REM Upgrade pip
python -m pip install --upgrade pip

REM Install dev dependencies
python -m pip install -r %~dp0\requirements-dev.txt

IF ERRORLEVEL 1 (
    echo Failed to install required packages
    exit /b 1
)

echo.
echo Installation complete!

ENDLOCAL
