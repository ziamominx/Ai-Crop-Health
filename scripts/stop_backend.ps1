# Stop any running Agricure backend (uvicorn) instances.
$conns = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
foreach ($c in $conns) {
    Stop-Process -Id $c.OwningProcess -Force -ErrorAction SilentlyContinue
    Write-Output ("killed listener pid " + $c.OwningProcess)
}
Get-CimInstance Win32_Process -Filter "Name like 'python%'" |
    Where-Object { $_.CommandLine -and $_.CommandLine.Contains('uvicorn') } |
    ForEach-Object {
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
        Write-Output ("killed uvicorn pid " + $_.ProcessId)
    }
Start-Sleep -Seconds 2
if (Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue) {
    Write-Output "port 8000: still-up"
} else {
    Write-Output "port 8000: down"
}
