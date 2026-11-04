$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$bundle = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies'
$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
if ($pythonCommand) { $pythonExe = $pythonCommand.Source } elseif (Test-Path "$bundle\python\python.exe") { $pythonExe = "$bundle\python\python.exe" } else { throw 'Installera Python 3.12 eller senare och lägg till Python i PATH.' }
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    if (Test-Path "$bundle\node\bin\node.exe") { $env:PATH = "$bundle\node\bin;$env:PATH" } else { throw 'Installera Node.js 22.12 eller senare.' }
}
$pnpmCommand = Get-Command pnpm.cmd -ErrorAction SilentlyContinue
if ($pnpmCommand) { $pnpmExe = $pnpmCommand.Source } elseif (Test-Path "$bundle\bin\fallback\pnpm.cmd") { $pnpmExe = "$bundle\bin\fallback\pnpm.cmd" } else { throw 'Installera pnpm med: npm install -g pnpm@11.25.0' }
if (-not (Test-Path '.venv\Scripts\python.exe')) { & $pythonExe -m venv .venv; if ($LASTEXITCODE -ne 0) { throw 'Kunde inte skapa Python-miljön.' } }
& .\.venv\Scripts\python.exe -m pip install -r requirements.lock
if ($LASTEXITCODE -ne 0) { throw 'Python-installationen misslyckades.' }
Push-Location frontend
try {
    & $pnpmExe install --frozen-lockfile
    if ($LASTEXITCODE -ne 0) { throw 'Frontend-installationen misslyckades.' }
    & $pnpmExe run build
    if ($LASTEXITCODE -ne 0) { throw 'Frontendbygget misslyckades.' }
} finally { Pop-Location }
if (-not (Test-Path '.env')) { Copy-Item -LiteralPath '.env.example' -Destination '.env' }
$env:PYTHONPATH = Join-Path (Get-Location) 'backend'
& .\.venv\Scripts\python.exe -m jarvis.cli owner
if ($LASTEXITCODE -ne 0) { throw 'Ägarkontot kunde inte skapas.' }
Write-Host 'Klart. Starta med: .\scripts\start.ps1'
