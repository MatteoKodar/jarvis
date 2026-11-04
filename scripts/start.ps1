param([switch]$OpenBrowser)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
Set-Location $projectRoot
$pythonExe = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path $pythonExe)) { throw 'Kör först .\scripts\setup.ps1' }
if (-not (Test-Path 'frontend\dist\index.html')) { throw 'Bygg först frontend, se README.' }
$env:PYTHONPATH = Join-Path $projectRoot 'backend'
# Run kan öppna den befintliga lokala instansen utan dubbla serverprocesser.
$existingPage = $null
try { $existingPage = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/' -UseBasicParsing -TimeoutSec 2 } catch { }
if ($existingPage -and $existingPage.StatusCode -eq 200) {
    if ($existingPage.Content -notmatch '(?i)jarvis') { throw 'Port 8000 används av ett annat program.' }
    Write-Host 'JARVIS är redan igång: http://127.0.0.1:8000/'
    if ($OpenBrowser) { Start-Process 'http://127.0.0.1:8000/' }
    return
}
New-Item -ItemType Directory -Force 'data\logs' | Out-Null
$backendProcess = Start-Process -FilePath $pythonExe -ArgumentList '-m uvicorn jarvis.api:app --host 127.0.0.1 --port 8000' -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput 'data\logs\api.log' -RedirectStandardError 'data\logs\api-error.log'
$workerProcess = Start-Process -FilePath $pythonExe -ArgumentList '-m jarvis.worker' -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput 'data\logs\worker.log' -RedirectStandardError 'data\logs\worker-error.log'
Write-Host 'JARVIS: http://127.0.0.1:8000'
Write-Host 'Låt detta fönster vara öppet. Webbläsaren kan stängas. Ctrl+C stoppar processerna.'
try {
    if ($OpenBrowser) {
        $ready = $false
        $deadline = (Get-Date).AddSeconds(30)
        while ((Get-Date) -lt $deadline -and -not $backendProcess.HasExited) {
            try {
                $response = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/' -UseBasicParsing -TimeoutSec 1
                if ($response.StatusCode -eq 200) { $ready = $true; break }
            } catch { }
            Start-Sleep -Milliseconds 300
        }
        if (-not $ready -or $backendProcess.HasExited) { throw 'JARVIS kunde inte starta. Kontrollera data\logs\api-error.log och om port 8000 redan används.' }
        Start-Process 'http://127.0.0.1:8000/'
    }
    while (-not $backendProcess.HasExited -and -not $workerProcess.HasExited) { Start-Sleep -Seconds 2 }
    Write-Host 'En process avslutades. Kontrollera data\logs.'
} finally {
    foreach ($process in @($backendProcess, $workerProcess)) {
        if (-not $process.HasExited) { & taskkill.exe /PID $process.Id /T /F | Out-Null }
    }
}
