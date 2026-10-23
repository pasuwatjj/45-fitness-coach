param([switch]$UpdateTunnel)
$ErrorActionPreference = "Stop"
$projectFolder = $PSScriptRoot
$localApi = "http://127.0.0.1:5000"
try {
    $status = Invoke-RestMethod -Uri "$localApi/status" -TimeoutSec 5
    $connection = Invoke-RestMethod -Uri "$localApi/connection" -TimeoutSec 5
} catch { throw "Start app.py in the FIRST PowerShell window, then run this in a SECOND window." }
if (!$connection.local_admin) { throw "Update the project to v14 first, then restart app.py." }
if ($connection.share_url) { throw "A share link is already registered. Stop the previous share window with Ctrl+C first." }
$toolFolder = Join-Path $projectFolder "tools"
$cloudflared = Join-Path $toolFolder "cloudflared.exe"
if ($UpdateTunnel -or !(Test-Path -LiteralPath $cloudflared)) {
    New-Item -ItemType Directory -Path $toolFolder -Force | Out-Null
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    $arch = if ([Environment]::Is64BitOperatingSystem) { "amd64" } else { "386" }
    $downloadUrl = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-$arch.exe"
    $partial = "$cloudflared.download"
    Write-Host "Downloading official Cloudflare Tunnel for Windows..."
    try {
        Invoke-WebRequest -Uri $downloadUrl -OutFile $partial -UseBasicParsing
        Move-Item -LiteralPath $partial -Destination $cloudflared -Force
    } catch { throw "Cloudflare download failed. Check internet access to github.com and run this again." }
}
$sessionFolder = Join-Path $env:TEMP ("45FitnessShare-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $sessionFolder | Out-Null
$outLog = Join-Path $sessionFolder "output.log"
$errLog = Join-Path $sessionFolder "error.log"
$tunnel = $null
$registered = $false
try {
    # This Host is mandatory: public visitors must never receive localhost access.
    $tunnel = Start-Process -FilePath $cloudflared -ArgumentList @(
        "tunnel", "--url", "http://127.0.0.1:5000", "--http-host-header", "45-public.invalid", "--no-autoupdate"
    ) -RedirectStandardOutput $outLog -RedirectStandardError $errLog -PassThru -WindowStyle Hidden
    Write-Host "Creating HTTPS share link. Keep both PowerShell windows open..."
    $deadline = (Get-Date).AddSeconds(90)
    while ($true) {
        if ($tunnel.HasExited) { throw "Tunnel exited. See $errLog" }
        $logText = ((Get-Content -LiteralPath $errLog -Raw -ErrorAction SilentlyContinue) +
                    (Get-Content -LiteralPath $outLog -Raw -ErrorAction SilentlyContinue))
        $match = [regex]::Match($logText, 'https://[a-z0-9-]+\.trycloudflare\.com')
        if ($match.Success) { break }
        if ((Get-Date) -gt $deadline) { throw "Tunnel connection timed out. Check internet or firewall. See $errLog" }
        Start-Sleep -Milliseconds 500
    }
    $payload = @{ base_url = $match.Value } | ConvertTo-Json
    $result = Invoke-RestMethod -Uri "$localApi/share/register" -Method Post -ContentType "application/json" -Body $payload -TimeoutSec 5
    $registered = $true
    Write-Host ""
    Write-Host "SHARE THIS COMPLETE LINK (including ?key=...):" -ForegroundColor Green
    Write-Host $result.share_url -ForegroundColor Cyan
    Write-Host ""
    Write-Host "The same link and QR appear under 'Share link' on your website."
    Write-Host "Each visitor signs in to a private email/password account."
    Write-Host "Each device uses its OWN camera. Frames are processed on this computer."
    Write-Host "Temporary test link: keep the computer, app.py and this window running."
    Write-Host "Press Ctrl+C HERE to stop sharing. This does not stop app.py."
    while (!$tunnel.HasExited) {
        Start-Sleep -Seconds 10
        try {
            $current = Invoke-RestMethod -Uri "$localApi/connection" -TimeoutSec 5
            if (!$current.share_url) {
                $restored = Invoke-RestMethod -Uri "$localApi/share/register" -Method Post -ContentType "application/json" -Body $payload -TimeoutSec 5
                Write-Host "Server reconnected to the existing temporary share link." -ForegroundColor Green
            }
        } catch { Write-Warning "Waiting for the local fitness server to return..." }
    }
    throw "The tunnel stopped. Run this script again to create a new link."
} finally {
    if ($null -ne $tunnel -and !$tunnel.HasExited) { Stop-Process -Id $tunnel.Id -ErrorAction SilentlyContinue }
    if ($registered) {
        try { Invoke-RestMethod -Uri "$localApi/share/register" -Method Post -ContentType "application/json" -Body '{"base_url":null}' -TimeoutSec 3 | Out-Null } catch {}
    }
}
