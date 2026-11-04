$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
Set-Location $projectRoot
$pythonExe = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path $pythonExe)) { throw 'Kör först .\scripts\setup.ps1' }
if (-not (Test-Path 'frontend\dist\index.html')) { throw 'Bygg först frontend, se README.' }
$env:PYTHONPATH = Join-Path $projectRoot 'backend'
New-Item -ItemType Directory -Force 'data\logs' | Out-Null
$backendProcess = Start-Process -FilePath $pythonExe -ArgumentList '-m uvicorn jarvis.api:app --host 127.0.0.1 --port 8000' -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput 'data\logs\api.log' -RedirectStandardError 'data\logs\api-error.log'
$workerProcess = Start-Process -FilePath $pythonExe -ArgumentList '-m jarvis.worker' -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput 'data\logs\worker.log' -RedirectStandardError 'data\logs\worker-error.log'
Write-Host 'JARVIS: http://127.0.0.1:8000'
Write-Host 'Låt detta fönster vara öppet. Webbläsaren kan stängas. Ctrl+C stoppar processerna.'
try {
    while (-not $backendProcess.HasExited -and -not $workerProcess.HasExited) { Start-Sleep -Seconds 2 }
    Write-Host 'En process avslutades. Kontrollera data\logs.'
} finally {
    foreach ($process in @($backendProcess, $workerProcess)) {
        if (-not $process.HasExited) { & taskkill.exe /PID $process.Id /T /F | Out-Null }
    }
}
