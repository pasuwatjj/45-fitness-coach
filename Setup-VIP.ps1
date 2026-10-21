$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot
Write-Host "Configure email and optional SlipOK. Secrets stay encrypted for this Windows user."
Write-Host "Register ONLY Kasikorn 0000000000 as the receiving account for this SlipOK branch."
$branch = Read-Host "SlipOK branch ID (press Enter for MANUAL review + email only)"
$confirmed = ""
$encryptedKey = ""
if ($branch) {
    if ($branch -notmatch '^\d+$') { throw "Branch ID must contain digits only." }
    $confirmed = Read-Host "Type 0000000000 AFTER registering that receiver in SlipOK"
    if ($confirmed -ne "0000000000") { throw "Receiver not confirmed. No settings saved." }
    $apiKey = Read-Host "SlipOK API key (hidden)" -AsSecureString
    $encryptedKey = ($apiKey | ConvertFrom-SecureString)
}
$smtpHost = Read-Host "SMTP server hostname from your email provider"
$smtpPort = Read-Host "SMTP port (587 STARTTLS or 465 SSL)"
if ($smtpPort -notin @("587","465")) { throw "Use TLS port 587 or 465." }
$smtpUser = Read-Host "Sender email / SMTP username"
$smtpPassword = Read-Host "SMTP app password (hidden; do not paste into chat)" -AsSecureString
if (!$smtpHost -or !$smtpUser) { throw "SMTP server and sender are required." }
$folder = Join-Path $PSScriptRoot "data"
New-Item -ItemType Directory -Force -Path $folder | Out-Null
$settings = @{
    branch = $branch
    receiver = $confirmed
    apiKey = $encryptedKey
    smtpHost = $smtpHost
    smtpPort = $smtpPort
    smtpUser = $smtpUser
    smtpPassword = ($smtpPassword | ConvertFrom-SecureString)
}
$settings | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $folder "vip-services.secure.json") -Encoding UTF8
Write-Host "Saved. Start with Start-Configured.ps1. Existing accounts and records were preserved." -ForegroundColor Green
& (Join-Path $PSScriptRoot "Start-Configured.ps1")
