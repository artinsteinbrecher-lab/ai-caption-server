# AI Caption 端口健康守护

- 用途：8000 监听失效时自动拉起后端，覆盖“进程存活但端口死亡”场景。
- 部署：将 `caption-port-watchdog.ps1` 放到 `C:\ops\`，然后注册每分钟运行的计划任务：

  ```powershell
  schtasks /create /tn "AI-Caption-Watchdog" /sc minute /mo 1 /ru SYSTEM /tr "powershell -NoProfile -ExecutionPolicy Bypass -File C:\ops\caption-port-watchdog.ps1" /f
  ```

- 关系：与启动 bat 的循环自拉起构成双层保护；bat 负责进程崩溃，守护脚本负责监听失效。
