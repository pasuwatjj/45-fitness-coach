$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot
# Keep Windows awake while this explicitly enabled background runner is alive.
Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public static class FitnessAwake {
 [DllImport("kernel32.dll")] public static extern uint SetThreadExecutionState(uint flags);
}
"@
[FitnessAwake]::SetThreadExecutionState([uint32]2147483649) | Out-Null
$env:FITNESS_PRODUCTION = "1"
$stopFlag = Join-Path $PSScriptRoot "data\stop-background.flag"
try {
while (!(Test-Path -LiteralPath $stopFlag)) {
    try { & (Join-Path $PSScriptRoot "Start-Configured.ps1") }
    catch { Write-Warning $_ }
    if (Test-Path -LiteralPath $stopFlag) { break }
    Start-Sleep -Seconds 5
}

} finally { [FitnessAwake]::SetThreadExecutionState([uint32]2147483648) | Out-Null }
