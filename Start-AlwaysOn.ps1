$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot
$dataPath = Join-Path $PSScriptRoot "data"
New-Item -ItemType Directory -Force -Path $dataPath | Out-Null
try { $live = Invoke-RestMethod -Uri "http://127.0.0.1:5000/status" -TimeoutSec 2 } catch { $live = $null }
if ($live) { throw "A server is already running. Stop its PowerShell window with Ctrl+C before using background mode." }
$pidFile = Join-Path $dataPath "background.json"
if (Test-Path -LiteralPath $pidFile) {
    $old = Get-Content -LiteralPath $pidFile -Raw | ConvertFrom-Json
    $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$($old.pid)"
    if ($proc -and $proc.CommandLine.Contains((Join-Path $PSScriptRoot "Keep-Running.ps1"))) { throw "Background runner is already active." }
}
Remove-Item -LiteralPath (Join-Path $dataPath "stop-background.flag") -ErrorAction SilentlyContinue
$runner = Join-Path $PSScriptRoot "Keep-Running.ps1"
$argsList = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ('"' + $runner + '"'))
$process = Start-Process powershell.exe -ArgumentList $argsList -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $dataPath "background-output.log") -RedirectStandardError (Join-Path $dataPath "background-errors.log") -PassThru
@{pid=$process.Id;runner=$runner} | ConvertTo-Json | Set-Content -LiteralPath $pidFile -Encoding UTF8
Write-Host "Background server started. You may close this window. Keep the PC powered on, awake and online." -ForegroundColor Green
Write-Host "Use Stop-AlwaysOn.ps1 to stop. Start-Share.ps1 still needs its own open window for the temporary mobile link."
