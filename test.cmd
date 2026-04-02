@echo off
SETLOCAL
set FAILED=0

echo ========================================
echo  Running Python tests (deep-mode-harness)
echo ========================================
call .venv\Scripts\activate
python -m pytest test/deep-mode-harness/
IF ERRORLEVEL 1 set FAILED=1

echo.
IF %FAILED%==1 (
    echo ========================================
    echo  RESULT: Some tests failed.
    echo ========================================
    exit /b 1
) ELSE (
    echo ========================================
    echo  RESULT: All tests passed.
    echo ========================================
    exit /b 0
)
ENDLOCAL
