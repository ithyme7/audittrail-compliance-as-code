@echo off
setlocal
cd /d "%~dp0\audittrail\dist"
if exist "audittrail-demo.exe" (
  echo Running AuditTrail demo exe...
  audittrail-demo.exe
) else (
  echo Demo exe not found. Running Python demo...
  cd /d "%~dp0\audittrail\demo"
  python fraud_detection_demo.py
)
echo.
echo Demo finished.
pause
