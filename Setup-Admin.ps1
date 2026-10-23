$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot
$pythonPath = Join-Path $PSScriptRoot "..\.venv\Scripts\python.exe"
if (!(Test-Path -LiteralPath $pythonPath)) { throw "Python environment not found: $pythonPath" }
& $pythonPath -X utf8 manage_admin.py --email "pasuwatoyasumi7@gmail.com"
if ($LASTEXITCODE -ne 0) { throw "Admin setup failed. Check the account exists in this project's database." }
