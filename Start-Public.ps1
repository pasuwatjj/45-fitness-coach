$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot
try { $connection = Invoke-RestMethod -Uri "http://127.0.0.1:5000/connection" -TimeoutSec 3 }
catch { $connection = $null }
if (!$connection) {
    & (Join-Path $PSScriptRoot "Start-AlwaysOn.ps1")
    $deadline = (Get-Date).AddSeconds(90)
    while (!$connection -and (Get-Date) -lt $deadline) {
        Start-Sleep -Seconds 2
        try { $connection = Invoke-RestMethod -Uri "http://127.0.0.1:5000/connection" -TimeoutSec 3 } catch {}
    }
}
if (!$connection) { throw "Server did not start. Read data/background-errors.log." }
if ($connection.share_url) {
    Write-Host "Share this HTTPS link (not 127.0.0.1):" -ForegroundColor Green
    Write-Host $connection.share_url -ForegroundColor Cyan
    Start-Process $connection.share_url
} else {
    & (Join-Path $PSScriptRoot "Start-Share.ps1")
}
