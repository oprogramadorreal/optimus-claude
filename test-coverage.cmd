@echo off
SETLOCAL
set FAILED=0

echo ========================================
echo  Python coverage (harness packages)
echo ========================================
echo  HTML report: htmlcov/
echo ========================================
call .venv\Scripts\activate
python -m pytest test/harness-common/ test/deep-mode-harness/ test/test-coverage-harness/ --cov=scripts/harness_common --cov=scripts/deep-mode-harness/impl --cov=scripts/test-coverage-harness --cov-report=term-missing --cov-report=html
IF ERRORLEVEL 1 set FAILED=1

echo.
IF %FAILED%==1 (
    echo ========================================
    echo  RESULT: Coverage check failed.
    echo ========================================
    exit /b 1
) ELSE (
    echo ========================================
    echo  RESULT: All coverage checks passed.
    echo ========================================
    echo  Report: htmlcov/index.html
    echo ========================================
    exit /b 0
)
ENDLOCAL
