# Supervised start script for Vittcott backend + frontend
# Launches backend (uvicorn) and frontend (Streamlit) each in a new PowerShell window
# and writes their stdout/stderr to logs in the repository `logs` directory.

$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$projectRoot = (Resolve-Path (Join-Path $scriptDir ".." )).ProviderPath

$python = Join-Path $projectRoot "backend\.venv\Scripts\python.exe"
$uvicorn_cwd = Join-Path $projectRoot "backend\src"
$streamlit_app = Join-Path $projectRoot "streamlit_app.py"
$logs = Join-Path $projectRoot "logs"

if (!(Test-Path $python)) {
    Write-Error "Python executable not found at $python. Ensure the backend venv exists and packages are installed."
    exit 2
}

if (!(Test-Path $streamlit_app)) {
    Write-Error "Streamlit app not found at $streamlit_app"
    exit 2
}

if (!(Test-Path $logs)) {
    New-Item -ItemType Directory -Path $logs | Out-Null
}

# Stop any previous uvicorn/streamlit processes we started earlier
$old = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'uvicorn|streamlit' }
if ($old) {
    Write-Host "Stopping existing uvicorn/streamlit processes..."
    $old | ForEach-Object {
        try { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue; Write-Host "Stopped PID $($_.ProcessId)" } catch {}
    }
}

# Start backend in a new PowerShell window and tee output to log
$backendLog = Join-Path $logs "backend.log"
$backendCmd = "Set-Location -Path '$uvicorn_cwd'; & '$python' -m uvicorn main:app --host 0.0.0.0 --port 8000 2>&1 | Tee-Object -FilePath '$backendLog'"
Start-Process -FilePath powershell.exe -ArgumentList "-NoExit","-Command","$backendCmd" -WorkingDirectory $uvicorn_cwd
Write-Host "Started backend (uvicorn). Log: $backendLog"

# Start Streamlit in a new PowerShell window, set backend URL env var, tee output to log
$streamlitLog = Join-Path $logs "streamlit.log"
$streamlitCmd = "Set-Location -Path '$projectRoot'; `$env:VITTCOTT_BACKEND_URL='http://localhost:8000'; & '$python' -m streamlit run '$streamlit_app' --server.port 8501 2>&1 | Tee-Object -FilePath '$streamlitLog'"
Start-Process -FilePath powershell.exe -ArgumentList "-NoExit","-Command","$streamlitCmd" -WorkingDirectory $projectRoot
Write-Host "Started Streamlit. Log: $streamlitLog"

Write-Host "\nServices started. To follow logs run (in PowerShell):"
Write-Host "  Get-Content -Path '$backendLog' -Wait -Tail 50"
Write-Host "  Get-Content -Path '$streamlitLog' -Wait -Tail 50"
