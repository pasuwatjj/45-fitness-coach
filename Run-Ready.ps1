$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot
try {
    $projectFolder = $PSScriptRoot
    if (!(Test-Path -LiteralPath (Join-Path $projectFolder "app.py"))) {
        Write-Host "1 = Select your EXISTING project (keeps accounts and history)"
        Write-Host "2 = Start a NEW project here (separate empty database)"
        $choice = Read-Host "Choose 1 or 2"
        if ($choice -eq "1") {
            Add-Type -AssemblyName System.Windows.Forms
            $picker = New-Object System.Windows.Forms.FolderBrowserDialog
            $picker.Description = "Select the EXISTING folder containing app.py and data"
            if ($picker.ShowDialog() -ne "OK") { return }
            $projectFolder = $picker.SelectedPath
            $picker.Dispose()
        } elseif ($choice -eq "2") {
            $projectFolder = $PSScriptRoot
        } else { return }
    }
    if (!(Test-Path -LiteralPath (Join-Path $projectFolder "app.py"))) { throw "Wrong folder: app.py was not found." }
    # Stop before copying if a server is still listening on our local port.
    $listener = Get-NetTCPConnection -LocalPort 5000 -State Listen -ErrorAction SilentlyContinue
    if ($listener) { throw "Port 5000 is in use. Stop the old website with Ctrl+C (or Stop-AlwaysOn.ps1), then retry." }
    $pythonPath = Join-Path $projectFolder "..\.venv\Scripts\python.exe"
    if (!(Test-Path -LiteralPath $pythonPath)) {
        $basePython = $null
        if (Get-Command py -ErrorAction SilentlyContinue) {
            foreach ($version in @("-3.11", "-3.12")) {
                $candidate = & py $version -c "import sys; print(sys.executable)" 2>$null
                if ($LASTEXITCODE -eq 0 -and $candidate) { $basePython = [string]$candidate; break }
            }
        }
        if (!$basePython -and (Get-Command python -ErrorAction SilentlyContinue)) {
            $candidate = & python -c "import sys; assert (3,9) <= sys.version_info[:2] <= (3,12); print(sys.executable)" 2>$null
            if ($LASTEXITCODE -eq 0) { $basePython = [string]$candidate }
        }
        if (!$basePython) { throw "Install 64-bit Python 3.11 or 3.12 from python.org first, then run START-HERE.cmd again." }
        $venvFolder = Join-Path $projectFolder "..\.venv"
        & $basePython -m venv $venvFolder
        if ($LASTEXITCODE -ne 0) { throw "Could not create the Python environment." }
    }
    if ([IO.Path]::GetFullPath($projectFolder) -ne [IO.Path]::GetFullPath($PSScriptRoot)) {
        & (Join-Path $PSScriptRoot "Install-Update.ps1") -projectFolder $projectFolder
    } else {
        & $pythonPath -m pip install -r (Join-Path $projectFolder "requirements.txt")
        if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed. Check internet and retry." }
        & (Join-Path $projectFolder "Start-Configured.ps1")
    }
} catch {
    Write-Host ""
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host "Take a screenshot of this message if you need help."
    exit 1
}
