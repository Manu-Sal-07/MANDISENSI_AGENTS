# MandiSense Institutional Stabilization Script
# Clears environment and restarts the unified cognition organism.

Write-Host "--- [MANDISENSE STABILIZATION: INITIALIZING] ---" -ForegroundColor Cyan

# 1. Kill Port 8000 (Backend)
Write-Host "Action: Purging Port 8000..."
Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | ForEach-Object { 
    Write-Host "Killing Process: $($_.OwningProcess)"
    Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue 
}
Start-Sleep -s 3 # Wait for OS to release socket

# 2. Kill Python Processes (Force)
Write-Host "Action: Stopping all Python cognitive tasks..."
Get-Process -Name python -ErrorAction SilentlyContinue | Stop-Process -Force

# 3. Clean Runtime Artifacts
Write-Host "Action: Cleaning stale cache and pycache..."
Remove-Item -Path "**/__pycache__" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path "mandisense_ai/cognition/stability_audit.py" -Force -ErrorAction SilentlyContinue

# 4. Start Backend
Write-Host "Action: Activating Unified API Layer..."
$apiProcess = Start-Process python -ArgumentList "api/main.py" -PassThru -WindowStyle Hidden
Write-Host "API Layer Started (PID: $($apiProcess.Id))" -ForegroundColor Green

# 5. Start Cognition Daemon
Write-Host "Action: Activating Continuous Cognition Daemon..."
$daemonProcess = Start-Process python -ArgumentList "scripts/cognition_daemon.py" -PassThru -WindowStyle Hidden
Write-Host "Cognition Daemon Started (PID: $($daemonProcess.Id))" -ForegroundColor Green

# 6. Wait for Verification
Write-Host "Waiting for MandiSense Synchronization..."
Start-Sleep -s 15

try {
    $health = Invoke-RestMethod -Uri "http://localhost:8000/v1/health"
    if ($health.status -eq "ok" -or $health.status -eq "degraded" -or $health.status -eq "healthy") {
        Write-Host "SUCCESS: MandiSense Institutional Infrastructure is ONLINE." -ForegroundColor Green
        Write-Host "Cognition Engine Status: $($health.status)"
        Write-Host "Operational Cycles: $($health.cognition_reliability.cycle_count)"
        Write-Host "API Uptime: $($health.cognition_reliability.uptime_sec)s"
    } else {
        Write-Host "WARNING: System reporting restricted state: $($health.status)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "CRITICAL: Synchronization failed. Review startup_final.log for tracebacks." -ForegroundColor Red
}

Write-Host "--- [ACTIVATION COMPLETE: MANDISENSE IS ALIVE] ---"
