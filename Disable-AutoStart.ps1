$ErrorActionPreference = "Stop"
Unregister-ScheduledTask -TaskName "45 Fitness Coach" -Confirm:$false
Write-Host "Auto-start removed. To stop the currently running server, use Stop-AlwaysOn.ps1."
