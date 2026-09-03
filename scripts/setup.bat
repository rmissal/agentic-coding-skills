@echo off
REM setup.bat — Windows launcher for scripts/setup.sh.
REM The real logic lives in setup.sh, which runs natively under Git Bash
REM (directory junctions via mklink /J need no admin rights).
where bash >nul 2>nul
if %ERRORLEVEL%==0 (
  bash "%~dp0setup.sh" %*
) else (
  echo Git Bash not found. Install Git for Windows ^(https://git-scm.com/download/win^),
  echo then re-run setup.bat, or run scripts/setup.sh from any bash shell.
  exit /b 1
)
