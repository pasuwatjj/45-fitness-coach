$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot
Write-Host "45 Fitness Coach - password reset email setup (no test email is sent)"
$smtpHost = Read-Host "SMTP host"
$smtpPort = Read-Host "SMTP port (587 or 465)"
if ($smtpPort -notin @("587", "465")) { throw "Use port 587 (STARTTLS) or 465 (TLS)." }
$smtpUser = Read-Host "Sender email / SMTP username"
$smtpPassword = Read-Host "SMTP password or app password" -AsSecureString
if ([string]::IsNullOrWhiteSpace($smtpHost) -or [string]::IsNullOrWhiteSpace($smtpUser) -or $smtpPassword.Length -eq 0) { throw "All fields are required." }
New-Item -ItemType Directory -Path (Join-Path $PSScriptRoot "data") -Force | Out-Null
@{smtpHost=$smtpHost;smtpPort=$smtpPort;smtpUser=$smtpUser;smtpPassword=($smtpPassword | ConvertFrom-SecureString)} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PSScriptRoot "data\email-service.secure.json") -Encoding UTF8
Write-Host "Saved for this Windows user. Restart Start-Configured.ps1 and keep the public HTTPS link running." -ForegroundColor Green
