# setup.ps1 — PowerShell launcher for scripts/setup.sh.
# The real logic lives in setup.sh, which runs natively under Git Bash on
# Windows (directory junctions via mklink /J need no admin rights).
$ErrorActionPreference = "Stop"
$bash = Get-Command bash -ErrorAction SilentlyContinue
if ($bash) {
    & bash "$PSScriptRoot/setup.sh" @args
    exit $LASTEXITCODE
} else {
    Write-Error "Git Bash not found. Install Git for Windows (https://git-scm.com/download/win), then re-run, or run scripts/setup.sh from any bash shell."
    exit 1
}
