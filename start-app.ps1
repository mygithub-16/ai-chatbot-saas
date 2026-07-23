$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$healthUrl = 'http://127.0.0.1:8000/health'
$siteUrl = 'http://127.0.0.1:8000/'
$stdoutLog = Join-Path $root 'backend-start.out.log'
$stderrLog = Join-Path $root 'backend-start.err.log'

try {
  Invoke-WebRequest -UseBasicParsing $healthUrl | Out-Null
  Write-Host "ECHURA is already running at $siteUrl"
  return
} catch {
  # Nothing is listening yet, so start the backend.
}

Start-Process `
  -WindowStyle Hidden `
  -FilePath 'python' `
  -ArgumentList '-m uvicorn backend.main:app --host 127.0.0.1 --port 8000' `
  -WorkingDirectory $root `
  -RedirectStandardOutput $stdoutLog `
  -RedirectStandardError $stderrLog

Start-Sleep -Seconds 8

try {
  Invoke-WebRequest -UseBasicParsing $healthUrl | Out-Null
  Write-Host "ECHURA is running at $siteUrl"
  Write-Host "Frontend assets are built automatically by backend startup."
} catch {
  Write-Host "The server started but the health check did not respond yet."
  Write-Host "Check the logs at $stdoutLog and $stderrLog"
}
