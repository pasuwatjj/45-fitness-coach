$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot
$pidFile = Join-Path $PSScriptRoot "data\background.json"
if (!(Test-Path -LiteralPath $pidFile)) { throw "No background runner record found." }
$record = Get-Content -LiteralPath $pidFile -Raw | ConvertFrom-Json
$proc = Get-CimInstance Win32_Process -Filter "ProcessId=$($record.pid)"
$expected = Join-Path $PSScriptRoot "Keep-Running.ps1"
if (!$proc -or !$proc.CommandLine.Contains($expected)) { throw "Recorded runner is not active. Nothing was stopped." }
try { Invoke-RestMethod -Uri "http://127.0.0.1:5000/local/cameras/reset" -Method Post -TimeoutSec 60 | Out-Null }
catch { throw "Camera save/reset did not complete. Server was not stopped: $_" }
New-Item -ItemType File -Force -Path (Join-Path $PSScriptRoot "data\stop-background.flag") | Out-Null
& taskkill.exe /PID $record.pid /T /F
if ($LASTEXITCODE -ne 0) { throw "Could not stop runner." }
Remove-Item -LiteralPath $pidFile
Write-Host "45 Fitness Coach background server stopped."
