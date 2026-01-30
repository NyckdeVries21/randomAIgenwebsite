<#
Run fetch and merge pipeline on Windows PowerShell.

Usage (from project root):
  .\scripts\run_fetch_and_merge.ps1

What it does:
- Checks for `python` or the `py` launcher
- Ensures `requests` is installed (uses pip via detected interpreter)
- Runs `scripts\run_fetch_and_merge.py`
#>
Set-StrictMode -Version Latest

Push-Location (Split-Path -Parent $MyInvocation.MyCommand.Definition)
Push-Location ..

function Find-Python {
    $py = Get-Command python -ErrorAction SilentlyContinue
    if ($py) { return $py.Source }
    $py3 = Get-Command py -ErrorAction SilentlyContinue
    if ($py3) { return "$($py3.Source) -3" }
    return $null
}

$pythonCmd = Find-Python
if (-not $pythonCmd) {
    Write-Error "Python not found. Install Python and enable 'Add Python to PATH', or ensure 'py' launcher is available."
    Exit 2
}

Write-Host "Using Python command: $pythonCmd"

# Ensure requests is installed
Write-Host "Checking for 'requests' package..."
try {
    & $pythonCmd -c "import requests" 2>$null
    if ($LASTEXITCODE -eq 0) { Write-Host "requests found." } else { throw "missing" }
} catch {
    Write-Host "Installing requests via pip..."
    & $pythonCmd -m pip install --upgrade pip
    & $pythonCmd -m pip install requests
    if ($LASTEXITCODE -ne 0) { Write-Error "Failed to install requests"; Exit 3 }
}

Write-Host "Running fetch-and-merge pipeline..."
& $pythonCmd scripts\run_fetch_and_merge.py
$rc = $LASTEXITCODE
if ($rc -ne 0) { Write-Error "Pipeline exited with code $rc"; Exit $rc }

Write-Host "Pipeline completed successfully. Check data/stats.json and data/ergast/."

Pop-Location
Pop-Location
