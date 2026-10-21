$ErrorActionPreference = "Stop"
$runner = Join-Path $PSScriptRoot "Start-AlwaysOn.ps1"
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument ('-NoProfile -ExecutionPolicy Bypass -File "' + $runner + '"') -WorkingDirectory $PSScriptRoot
$trigger = New-ScheduledTaskTrigger -AtLogOn -User ([Security.Principal.WindowsIdentity]::GetCurrent().Name)
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit ([TimeSpan]::Zero) -StartWhenAvailable
Register-ScheduledTask -TaskName "45 Fitness Coach" -Action $action -Trigger $trigger -Settings $settings -Description "Start the fitness server after this user signs in" -Force | Out-Null
Write-Host "Auto-start enabled for your next Windows sign-in. Keep the computer powered and online. Temporary sharing still needs Start-Share.ps1."
