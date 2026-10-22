# NEXAI Platform -- Stop All Portals
# Run: .\stop_all.ps1

Write-Host "Stopping all NEXAI Portal processes on ports 8500, 8501, 8502, 8503..." -ForegroundColor Yellow

$ports = @(8500, 8501, 8502, 8503)
foreach ($port in $ports) {
    $connections = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    if ($connections) {
        $pids = $connections | Select-Object -ExpandProperty OwningProcess -Unique
        foreach ($p in $pids) {
            Write-Host "Terminating process ID $p on port $port..." -ForegroundColor Gray
            Stop-Process -Id $p -Force -ErrorAction SilentlyContinue
        }
    }
}

Write-Host "All NEXAI Portals stopped successfully." -ForegroundColor Green
