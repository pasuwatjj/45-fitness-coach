param([string]$projectFolder = "D:\Robot Project\FitnessFormCoach_Python\FitnessFormCoach_Python")
$ErrorActionPreference = "Stop"
$pythonPath = Join-Path $projectFolder "..\.venv\Scripts\python.exe"
$sourceFolder = $PSScriptRoot

if (!(Test-Path -LiteralPath "$projectFolder\app.py")) {
    throw "Project app.py not found: $projectFolder"
}
if (!(Test-Path -LiteralPath $pythonPath)) {
    throw "Existing Python environment not found: $pythonPath"
}
if ([System.IO.Path]::GetFullPath($sourceFolder) -eq [System.IO.Path]::GetFullPath($projectFolder)) {
    throw "Run this installer from the freshly extracted UPDATE ZIP, not the project folder."
}
if (!(Select-String -LiteralPath "$sourceFolder\app.py" -Pattern "GENTLE_COACH_VERSION = 24" -SimpleMatch -Quiet)) {
    throw "This is not the latest v24 update."
}

$stamp = Get-Date -Format "yyyyMMdd-HHmmss-fff"
$backupFolder = Join-Path $projectFolder "backup-$stamp"
New-Item -ItemType Directory -Path $backupFolder | Out-Null
$updateItems = @(
    "test_v24.py", "V24_README_TH.txt", "TEST_REPORT_V24.txt",
    "OPEN-WEBSITE.cmd", "OPEN-MOBILE-LINK.cmd",
    "password_mail.py", "Setup-Email.ps1", "test_v23.py", "test_ui_v23.cjs", "V23_README_TH.txt", "TEST_REPORT_V23.txt",
    "V22_README_TH.txt", "TEST_REPORT_V22.txt",
    "Setup-Permanent-Link.ps1", "V21_README_TH.txt", "TEST_REPORT_V21.txt",
    "progress_analysis.py", "test_v20.py", "Start-Public.ps1", "V20_README_TH.txt", "TEST_REPORT_V20.txt",
    "angles.py", "share_access.py", "collaboration_features.py", "test_v20.py", "V19_README_TH.txt", "compose.yaml", "Caddyfile", "Enable-AutoStart.ps1", "Disable-AutoStart.ps1",
    "cardio.py", "test_v18.py", "V18_README_TH.txt", "TEST_REPORT_V18.txt",
    "community.py", "manage_admin.py", "serve.py", "Dockerfile", ".dockerignore", "Setup-Admin.ps1", "Reset-Camera.ps1", "Keep-Running.ps1", "Start-AlwaysOn.ps1", "Stop-AlwaysOn.ps1", "test_v16.py", "V16_README_TH.txt", "HOSTING_README_TH.txt",
    "app.py", "curl_counter.py", "form_rules.py", "leaderboard.py", "voice.py", "health.py",
    "exercises.py", "motion_coach.py", "planner.py", "accounts.py", "recovery.py", "visitors.py", "V14_README_TH.txt", "sessions.py", "grip.py", "profile_data.py", "strict_form.py", "rewards.py", "challenges.py", "membership.py", "shop.py", "check_services.py", "manage_shop.py", "Setup-VIP.ps1", "Start-Configured.ps1", "VIP_SETUP_TH.txt", "localization.py", "exercise_images.json", "Start-Share.ps1",
    "settings.json", "requirements.txt", "README.txt", "ATTRIBUTION.txt",
    "test_form_rules.py", "test_gentle_coach.py", "test_health_voice.py", "test_planner_motion.py", "test_sessions.py", "test_v8.py", "test_v9.py", "test_v10.py", "test_v11.py", "test_v12.py", "test_v13.py", "test_v14.py",
    "UPDATE_POWERSHELL.txt", "QUICK_START_TH.txt", "Install-Update.ps1", "OPENAI_VOICE_SETUP.txt", "templates", "static"
)
foreach ($name in $updateItems) {
    $newPath = Join-Path $sourceFolder $name
    if (!(Test-Path -LiteralPath $newPath)) { throw "Incomplete update: $name" }
}
foreach ($name in $updateItems) {
    $oldPath = Join-Path $projectFolder $name
    if (Test-Path -LiteralPath $oldPath) {
        Copy-Item -LiteralPath $oldPath -Destination $backupFolder -Recurse
    }
}
foreach ($name in $updateItems) {
    Copy-Item -LiteralPath (Join-Path $sourceFolder $name) -Destination $projectFolder -Recurse -Force
}
Set-Location -LiteralPath $projectFolder
& $pythonPath -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    throw "Dependency installation failed. Check internet and retry. Backup: $backupFolder"
}
if ($LASTEXITCODE -ne 0) { Write-Warning "Admin account not found. Sign in and run Setup-Admin.ps1 afterwards." }
Write-Host "45 Fitness Coach v24 updated." -ForegroundColor Green
Write-Host "Backup: $backupFolder"
Write-Host "For a public mobile link, run Start-Share.ps1 in a SECOND PowerShell window."
Write-Host "Open http://127.0.0.1:5000/45-fitness-coach and press Ctrl+F5."
& (Join-Path $projectFolder "Start-Configured.ps1")