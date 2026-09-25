@echo off
setlocal
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (echo Run install.cmd first. & exit /b 1)
.venv\Scripts\python.exe -m pytest test/harness-common/ --cov=scripts/harness_common --cov-report=term-missing --cov-report=html && echo Report: htmlcov\index.html
