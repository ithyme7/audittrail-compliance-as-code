@echo off
setlocal EnableExtensions EnableDelayedExpansion

set ROOT=%~dp0

echo ===============================
echo AuditTrail One-Click Runner
echo ===============================

echo.
echo [1/4] Installing dependencies (demo + dashboard + pdf)...
cd /d "%ROOT%audittrail\sdk-python"
python -m pip install -e ".[demo,dashboard,pdf]"
if errorlevel 1 goto :error

echo.
echo [2/4] Running demo (generates logs + report)...
cd /d "%ROOT%audittrail\demo"
python fraud_detection_demo.py
if errorlevel 1 goto :error

echo.
echo [3/4] Exporting latest PDF report...
set LATEST=
for /f "delims=" %%F in ('dir /b /o:-d ".\demo_output\fraud-detection-demo_compliance_report_*.json" 2^>nul') do (
  set LATEST=%%F
  goto :found
)
:found
if not defined LATEST (
  echo No compliance report found. Skipping PDF export.
) else (
  python pdf_exporter.py ".\demo_output\!LATEST!"
)

echo.
echo [4/4] Starting dashboard...
streamlit run dashboard.py
goto :eof

:error
echo.
echo ERROR: Something failed. Please scroll up for details.
pause
