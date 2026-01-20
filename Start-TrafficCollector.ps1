<#
.SYNOPSIS
    Smart Traffic Data Collector Management Script

.DESCRIPTION
    Manages the Gurugram traffic data collection scheduler.
    - Peak hours (6 AM - 9 PM): Collects every 10 minutes
    - Off-peak (9 PM - 6 AM): Collects every 60 minutes
    - Total: ~2,475 API calls/day (within 2,500 free limit)

.PARAMETER Action
    start    - Start collector in foreground
    daemon   - Start collector in background
    status   - Check if collector is running
    stop     - Stop the collector
    install  - Create Windows Task Scheduler entry (auto-start on boot)
    uninstall - Remove Windows Task Scheduler entry

.EXAMPLE
    .\Start-TrafficCollector.ps1 start
    .\Start-TrafficCollector.ps1 daemon
    .\Start-TrafficCollector.ps1 status
    .\Start-TrafficCollector.ps1 stop
    .\Start-TrafficCollector.ps1 install
#>

param(
    [Parameter(Position=0)]
    [ValidateSet("start", "daemon", "status", "stop", "install", "uninstall", "help")]
    [string]$Action = "help"
)

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$SchedulerScript = Join-Path $ProjectRoot "collector\run_scheduler.py"
$TaskName = "GurgaonTrafficCollector"

function Write-Banner {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "  Gurugram Traffic Data Collector" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
}

function Start-Foreground {
    Write-Banner
    Write-Host "Starting collector in foreground (Ctrl+C to stop)..." -ForegroundColor Yellow
    Write-Host ""
    Set-Location $ProjectRoot
    python $SchedulerScript
}

function Start-Daemon {
    Write-Banner
    Write-Host "Starting collector in background..." -ForegroundColor Yellow
    Set-Location $ProjectRoot
    python $SchedulerScript --daemon
}

function Get-Status {
    Write-Banner
    Set-Location $ProjectRoot
    python $SchedulerScript --status
}

function Stop-Collector {
    Write-Banner
    Write-Host "Stopping collector..." -ForegroundColor Yellow
    Set-Location $ProjectRoot
    python $SchedulerScript --stop
}

function Install-Task {
    Write-Banner
    Write-Host "Creating Windows Task Scheduler entry..." -ForegroundColor Yellow
    
    # Check for admin rights
    $isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    
    if (-not $isAdmin) {
        Write-Host "ERROR: Administrator privileges required to create scheduled task." -ForegroundColor Red
        Write-Host "Please run PowerShell as Administrator and try again." -ForegroundColor Yellow
        return
    }
    
    # Create the scheduled task
    $pythonPath = (Get-Command python).Source
    $action = New-ScheduledTaskAction -Execute $pythonPath -Argument "`"$SchedulerScript`"" -WorkingDirectory $ProjectRoot
    $trigger = New-ScheduledTaskTrigger -AtStartup
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
    $principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
    
    # Register the task
    try {
        Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force | Out-Null
        Write-Host "SUCCESS: Task '$TaskName' created!" -ForegroundColor Green
        Write-Host ""
        Write-Host "The collector will now start automatically when Windows boots." -ForegroundColor Cyan
        Write-Host "To start it now, run: .\Start-TrafficCollector.ps1 daemon" -ForegroundColor Cyan
    }
    catch {
        Write-Host "ERROR: Failed to create task: $_" -ForegroundColor Red
    }
}

function Uninstall-Task {
    Write-Banner
    Write-Host "Removing Windows Task Scheduler entry..." -ForegroundColor Yellow
    
    try {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction Stop
        Write-Host "SUCCESS: Task '$TaskName' removed!" -ForegroundColor Green
    }
    catch {
        Write-Host "Task '$TaskName' not found or already removed." -ForegroundColor Yellow
    }
}

function Show-Help {
    Write-Banner
    Write-Host "Usage: .\Start-TrafficCollector.ps1 <action>" -ForegroundColor White
    Write-Host ""
    Write-Host "Actions:" -ForegroundColor Yellow
    Write-Host "  start     - Run collector in foreground (see live output)"
    Write-Host "  daemon    - Run collector in background"
    Write-Host "  status    - Check if collector is running"
    Write-Host "  stop      - Stop the background collector"
    Write-Host "  install   - Auto-start collector on Windows boot (requires Admin)"
    Write-Host "  uninstall - Remove auto-start entry"
    Write-Host "  help      - Show this help"
    Write-Host ""
    Write-Host "Schedule:" -ForegroundColor Yellow
    Write-Host "  Peak hours (6 AM - 9 PM):  Every 10 minutes"
    Write-Host "  Off-peak (9 PM - 6 AM):    Every 60 minutes"
    Write-Host "  Daily API calls: ~2,475 (within 2,500 free limit)"
    Write-Host ""
}

# Main execution
switch ($Action) {
    "start"     { Start-Foreground }
    "daemon"    { Start-Daemon }
    "status"    { Get-Status }
    "stop"      { Stop-Collector }
    "install"   { Install-Task }
    "uninstall" { Uninstall-Task }
    "help"      { Show-Help }
}
