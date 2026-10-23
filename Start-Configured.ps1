$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot
$pythonPath = Join-Path $PSScriptRoot "..\.venv\Scripts\python.exe"
if (!(Test-Path -LiteralPath $pythonPath)) { throw "Python environment not found: $pythonPath" }
$publicConfigPath = Join-Path $PSScriptRoot "data\public-site.json"
if (Test-Path -LiteralPath $publicConfigPath) {
    $publicConfig = Get-Content -LiteralPath $publicConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $env:FITNESS_PUBLIC_URL = [string]$publicConfig.public_url
}
$configPath = Join-Path $PSScriptRoot "data\vip-services.secure.json"
function Unprotect-LocalSecret([string]$Encrypted) {
    $secure = $Encrypted | ConvertTo-SecureString
    $pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try { return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer) }
    finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer) }
}
try {
    Remove-Item Env:FITNESS_SERVICES_OK -ErrorAction SilentlyContinue
    if (Test-Path -LiteralPath $configPath) {
        $config = Get-Content -LiteralPath $configPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $env:FITNESS_SLIPOK_BRANCH = $config.branch
        $env:FITNESS_RECEIVER_CONFIRMED = $config.receiver
        $env:FITNESS_SLIPOK_KEY = if ($config.apiKey) { Unprotect-LocalSecret $config.apiKey } else { "" }
        $env:FITNESS_SMTP_HOST = $config.smtpHost
        $env:FITNESS_SMTP_PORT = $config.smtpPort
        $env:FITNESS_SMTP_USER = $config.smtpUser
        $env:FITNESS_SMTP_PASSWORD = Unprotect-LocalSecret $config.smtpPassword
        & $pythonPath -X utf8 check_services.py
        if ($LASTEXITCODE -eq 0) { $env:FITNESS_SERVICES_OK = "1" }
        else { Write-Warning "Automatic verification unavailable. VIP receipts require manual bank-transfer review." }
    }
    $emailConfigPath = Join-Path $PSScriptRoot "data\email-service.secure.json"
    if (Test-Path -LiteralPath $emailConfigPath) {
        $emailConfig = Get-Content -LiteralPath $emailConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $env:FITNESS_SMTP_HOST = $emailConfig.smtpHost
        $env:FITNESS_SMTP_PORT = $emailConfig.smtpPort
        $env:FITNESS_SMTP_USER = $emailConfig.smtpUser
        $env:FITNESS_SMTP_PASSWORD = Unprotect-LocalSecret $emailConfig.smtpPassword
    }
    if ($env:FITNESS_PRODUCTION -eq "1") { & $pythonPath -X utf8 serve.py }
    else { & $pythonPath -X utf8 app.py }
} finally {
    Remove-Item Env:FITNESS_SLIPOK_KEY -ErrorAction SilentlyContinue
    Remove-Item Env:FITNESS_SMTP_PASSWORD -ErrorAction SilentlyContinue
    Remove-Item Env:FITNESS_SERVICES_OK -ErrorAction SilentlyContinue
}
