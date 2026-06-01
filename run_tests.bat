@echo off
REM ============================================================================
REM run_tests.bat - Windows launcher for the EscapeCircuit test suite.
REM Forwards to run_tests.ps1 (bypassing the PowerShell execution policy so it
REM works on any Windows PC without changing system settings).
REM
REM   run_tests.bat            run everything
REM   run_tests.bat backend    backend only
REM   run_tests.bat frontend   frontend only
REM ============================================================================
setlocal
set "MODE=%~1"
if "%MODE%"=="" set "MODE=all"

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_tests.ps1" %MODE%
exit /b %ERRORLEVEL%
