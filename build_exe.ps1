Set-StrictMode -Version Latest

$root = "C:\Users\thyme\Downloads\SaaS\audittrail"
$sdk = Join-Path $root "sdk-python"
$demo = Join-Path $root "demo"
$dist = Join-Path $root "dist"

if (-not (Test-Path $dist)) {
    New-Item -ItemType Directory -Path $dist | Out-Null
}

Write-Host "Installing build dependencies..."
Push-Location $sdk
pip install -e ".[demo,test,exe]" | Out-Host

Write-Host "Building SDK CLI exe..."
pyinstaller --onefile --name audittrail-cli --distpath $dist --paths $sdk --collect-all audittrail (Join-Path $sdk "audittrail\cli.py")
Pop-Location

Write-Host "Building demo exe..."
Push-Location $demo
pyinstaller --onefile --name audittrail-demo --distpath $dist --paths $sdk --collect-all audittrail (Join-Path $demo "fraud_detection_demo.py")
Pop-Location

Write-Host "Done. EXEs are in $dist"
