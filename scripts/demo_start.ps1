<#
Demo start script (PowerShell) - simplified and robust
- Creates the backend virtual environment if missing
- Installs requirements if not already installed
- Runs the supervised start_all.ps1 to launch backend + frontend
- Opens the browser to Streamlit at http://localhost:8501

Usage: from repo root:
  powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\demo_start.ps1
#>

$ErrorActionPreference = 'Stop'

# Minimal demo starter - simplified for robustness
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$projectRoot = (Resolve-Path (Join-Path $scriptDir '..')).ProviderPath
$venvPath = Join-Path $projectRoot 'backend\.venv'
$python = Join-Path $venvPath 'Scripts\python.exe'
$requirements = Join-Path $projectRoot 'backend\requirements.txt'
$startAll = Join-Path $projectRoot 'scripts\start_all.ps1'

Write-Host 'Project root:' $projectRoot

if (!(Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error 'Python not found in PATH. Install Python 3.11+ and retry.'
    exit 2
}

if (!(Test-Path $venvPath)) {
    Write-Host 'Creating virtual environment...'
    & python -m venv $venvPath
}

if (!(Test-Path $python)) {
    Write-Error "Venv python not found at $python"
    exit 2
}

Write-Host 'Upgrading pip and installing requirements (if present)'
& $python -m pip install --upgrade pip | Out-Null
if (Test-Path $requirements) { & $python -m pip install -r $requirements }

Write-Host 'Launching supervised start script...'
Start-Process -FilePath powershell.exe -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File',"$startAll"
Start-Sleep -Seconds 2

Write-Host 'Opening http://localhost:8501 in default browser'
Start-Process 'http://localhost:8501'

Write-Host 'Demo launched. Tail logs with:'
Write-Host "  Get-Content -Path .\logs\backend.log -Wait -Tail 50"
Write-Host "  Get-Content -Path .\logs\streamlit.log -Wait -Tail 50"
