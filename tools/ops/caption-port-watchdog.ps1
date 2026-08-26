$port = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if (-not $port) {
$log = "C:\ops\watchdog.log"
Add-Content $log "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') 8000 未监听，执行恢复"
Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
Where-Object { $_.CommandLine -match 'app.py' } |
ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
Start-Sleep -Seconds 3
schtasks /run /tn "AI-Caption-Backend" | Out-Null
Start-Sleep -Seconds 15
$after = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
Add-Content $log "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') 恢复结果: $(if($after){'成功'}else{'失败'})"
}
