@echo off
REM ============================================
REM Smart Traffic Collector - Windows Launcher
REM ============================================

cd /d "%~dp0"

echo.
echo ========================================
echo   Gurugram Traffic Data Collector
echo ========================================
echo.

if "%1"=="--daemon" goto daemon
if "%1"=="--status" goto status
if "%1"=="--stop" goto stop
if "%1"=="--help" goto help

REM Default: run in foreground
echo Starting collector in foreground (Ctrl+C to stop)...
python collector/run_scheduler.py
goto end

:daemon
echo Starting collector in background...
python collector/run_scheduler.py --daemon
goto end

:status
python collector/run_scheduler.py --status
goto end

:stop
python collector/run_scheduler.py --stop
goto end

:help
echo Usage: start_collector.bat [option]
echo.
echo Options:
echo   (no option)   Run in foreground (see live output)
echo   --daemon      Run in background (detached)
echo   --status      Check if collector is running
echo   --stop        Stop the background collector
echo   --help        Show this help
echo.

:end
