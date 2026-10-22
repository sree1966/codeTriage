# NEXAI Platform -- Launch All Four Portals
# Run: .\start_all.ps1

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   NEXAI -- Multi-Portal Intelligent Support Platform     " -ForegroundColor Yellow
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Stop any stale processes listening on ports 8500-8503
$ports = @(8500, 8501, 8502, 8503)
Write-Host "Checking for stale processes on ports $($ports -join ', ')..." -ForegroundColor Gray

foreach ($port in $ports) {
    $connections = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    if ($connections) {
        $pids = $connections | Select-Object -ExpandProperty OwningProcess -Unique
        foreach ($p in $pids) {
            Write-Host "Freeing port $port (stopping process ID $p)..." -ForegroundColor Yellow
            Stop-Process -Id $p -Force -ErrorAction SilentlyContinue
        }
    }
}
Start-Sleep -Seconds 1

# 2. Get script directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

Write-Host "`nLaunching NEXAI Portals..." -ForegroundColor Green

# 3. Launch each Streamlit application directly with Python
Start-Process python -ArgumentList "-m", "streamlit", "run", "portal_home.py", "--server.port", "8500", "--server.headless", "true" -WorkingDirectory $scriptDir
Start-Process python -ArgumentList "-m", "streamlit", "run", "app.py", "--server.port", "8501", "--server.headless", "true" -WorkingDirectory $scriptDir
Start-Process python -ArgumentList "-m", "streamlit", "run", "human_portal.py", "--server.port", "8502", "--server.headless", "true" -WorkingDirectory $scriptDir
Start-Process python -ArgumentList "-m", "streamlit", "run", "admin_portal.py", "--server.port", "8503", "--server.headless", "true" -WorkingDirectory $scriptDir

Start-Sleep -Seconds 3

Write-Host "`n==========================================================" -ForegroundColor Cyan
Write-Host "   NEXAI SERVICES STARTED SUCCESSFULLY                    " -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " [Portal Home]   : http://localhost:8500" -ForegroundColor White
Write-Host " [Customer App]  : http://localhost:8501" -ForegroundColor Cyan
Write-Host " [Human Portal]  : http://localhost:8502" -ForegroundColor Green
Write-Host " [Admin Portal]  : http://localhost:8503" -ForegroundColor Magenta
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Admin Credentials: Username: admin | Password: nexai2026" -ForegroundColor Gray
Write-Host "To stop all services anytime, run: .\stop_all.ps1`n" -ForegroundColor Yellow

# Launch portal home in default browser
Start-Process "http://localhost:8500"
