$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $repoRoot ".venv\Scripts\python.exe"
$mainPy = Join-Path $repoRoot "src\main.py"
$logFile = Join-Path $repoRoot "state\run.log"

$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Add-Content -Path $logFile -Value "----- $timestamp -----"

try {
    & $python $mainPy 2>&1 | Add-Content -Path $logFile
} catch {
    Add-Content -Path $logFile -Value "Launcher error: $_"
}
