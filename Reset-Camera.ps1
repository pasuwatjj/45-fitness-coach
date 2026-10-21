$ErrorActionPreference = "Stop"
# Local owner recovery: saves and resets ALL browser camera sessions; no server restart.
$result = Invoke-RestMethod -Uri "http://127.0.0.1:5000/local/cameras/reset" -Method Post -TimeoutSec 60
Write-Host "Reset $($result.reset_sessions) camera sessions. Press Reset camera, then Start in the browser." -ForegroundColor Green
