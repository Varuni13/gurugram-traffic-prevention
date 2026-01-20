@echo off
REM ============================================
REM Gurugram Traffic Collector - Background Runner
REM This script runs silently in the background
REM ============================================

cd /d "c:\Users\Varuni Singh\AIResqClimsol\Gurugram Mobility\gurugram-traffic-prevention"

REM Start Python scheduler (runs forever)
C:\Python313\python.exe collector\run_scheduler.py
