# AI字幕设备后端 — Windows Server 部署指南

基于实际部署经验整理，涵盖腾讯云 Windows Server 上的完整部署流程和踩坑记录。

## 环境信息

- 腾讯云轻量应用服务器 Windows Server，4核4G
- 公网 IP 访问（无域名）
- Python 3.11 + Git + pip 直接部署（不用 Docker、不用 Conda）

## 部署步骤

### 第一步：安装 Python

从华为镜像下载（python.org 在国内很慢）：

```powershell
Invoke-WebRequest -Uri "https://mirrors.huaweicloud.com/python/3.11.9/python-3.11.9-amd64.exe" -OutFile "$env:TEMP\python-installer.exe"
Start-Process -FilePath "$env:TEMP\python-installer.exe" -Wait
```

安装时**务必勾选** "Add Python to PATH"。

> **踩坑**：安装完成后，当前 PowerShell 窗口的 PATH 不会自动刷新，`python` 命令仍然找不到。必须**关闭当前窗口，重新打开一个新的 PowerShell**。

验证：

```powershell
python --version
```

### 第二步：安装 Git

从 npmmirror 下载：

```powershell
Invoke-WebRequest -Uri "https://registry.npmmirror.com/-/binary/git-for-windows/v2.45.0.windows.1/Git-2.45.0-64-bit.exe" -OutFile "$env:TEMP\git-installer.exe"
Start-Process -FilePath "$env:TEMP\git-installer.exe" -Wait
```

一路下一步即可。装完**重开 PowerShell**，验证：

```powershell
git --version
```

### 第三步：克隆后端代码

```powershell
cd C:\
git clone https://github.com/artinsteinbrecher-lab/ai-caption-server.git
```

> **踩坑**：国内服务器直连 GitHub 会被 GFW 拦截，报 `Connection was reset`。即使服务器装了 VPN（如 FlClash），git 默认不走系统代理。FlClash 用 TUN 模式时不监听 HTTP 代理端口，`git config --global http.proxy` 也用不了。
>
> **解决方案**：用 GitHub 代理下载 ZIP：
> ```powershell
> Invoke-WebRequest -Uri "https://gh-proxy.com/https://github.com/artinsteinbrecher-lab/ai-caption-server/archive/refs/heads/master.zip" -OutFile "C:\ai-caption.zip"
> Expand-Archive -Path "C:\ai-caption.zip" -DestinationPath "C:\" -Force
> Rename-Item "C:\ai-caption-server-master" "C:\ai-caption-server"
> ```
>
> 注意：gitclone.com 镜像对新仓库可能返回空仓库，不推荐用。

### 第四步：安装 Python 依赖

```powershell
cd C:\ai-caption-server\main\xiaozhi-server
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

用清华镜像源速度快很多。如果个别包没装上，再跑一次用默认源补装：

```powershell
pip install -r requirements.txt
```

> **踩坑**：第一次安装可能不完整，后续启动时会报 `ModuleNotFoundError`。缺什么就单独装什么，比如 `pip install aioconsole`。

### 第五步：安装 Opus 音频编解码库

`opuslib_next` 需要 native opus.dll，Windows 上不会自动安装。

从 NuGet 包 `DSharpPlus.Natives.Opus` 提取 opus.dll：

```powershell
Invoke-WebRequest -Uri "https://www.nuget.org/api/v2/package/DSharpPlus.Natives.Opus" -OutFile "$env:TEMP\opus-pkg.zip"
```

```powershell
Expand-Archive "$env:TEMP\opus-pkg.zip" -DestinationPath "$env:TEMP\opus-pkg" -Force
```

```powershell
Copy-Item "$env:TEMP\opus-pkg\runtimes\win-x64\native\opus.dll" "C:\Windows\System32\opus.dll"
```

> **踩坑**：NuGet 包 `opus.win32` 不存在（返回 BlobNotFound），不要用。正确包名是 `DSharpPlus.Natives.Opus`，里面有 win-x64 和 win-arm64 两个版本，用 win-x64。

### 第六步：安装 FFmpeg

从 gyan.dev 下载：

```powershell
Invoke-WebRequest -Uri "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip" -OutFile "$env:TEMP\ffmpeg.zip"
```

```powershell
Expand-Archive "$env:TEMP\ffmpeg.zip" -DestinationPath "C:\ffmpeg" -Force
```

FFmpeg 解压后 bin 目录在子目录里，先找到实际路径：

```powershell
Get-ChildItem -Path "C:\ffmpeg" -Recurse -Filter "ffmpeg.exe" | Select-Object FullName
```

输出类似 `C:\ffmpeg\ffmpeg-8.1.1-essentials_build\bin\ffmpeg.exe`。把这个 bin 目录加入 PATH：

```powershell
[Environment]::SetEnvironmentVariable("Path", [Environment]::GetEnvironmentVariable("Path", "Machine") + ";C:\ffmpeg\ffmpeg-8.1.1-essentials_build\bin", "Machine")
```

```powershell
$env:Path += ";C:\ffmpeg\ffmpeg-8.1.1-essentials_build\bin"
```

验证：

```powershell
ffmpeg -version
```

> **踩坑**：gyan.dev 的 zip 解压后 bin 不在 `C:\ffmpeg\bin`，而是在 `C:\ffmpeg\ffmpeg-X.X.X-essentials_build\bin`。版本号不同路径也不同，必须用 `Get-ChildItem -Recurse -Filter ffmpeg.exe` 找实际路径。

### 第七步：创建配置文件

```powershell
cd C:\ai-caption-server\main\xiaozhi-server
mkdir data
notepad data\.config.yaml
```

在记事本中粘贴以下内容，修改两处占位符后保存：

```yaml
server:
  websocket: ws://你的公网IP:8000/xiaozhi/v1/
  vision_explain: http://你的公网IP:8003/mcp/vision/explain

ASR:
  AliyunBLStreamASR:
    api_key: 你的阿里云百炼API密钥

caption_mode: true
enable_websocket_ping: true
```

- 公网 IP：在服务器浏览器打开 https://api.ipify.org 查看
- API Key：在 https://bailian.console.aliyun.com/#/api-key 获取

> **注意**：配置文件路径必须是 `data\.config.yaml`（注意文件名以点开头）。如果放在了其他位置，服务端不会读取。

### 第八步：开放防火墙端口

Windows 防火墙（PowerShell 管理员）：

```powershell
New-NetFirewallRule -DisplayName "AI-Caption-8000" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8000
```

```powershell
New-NetFirewallRule -DisplayName "AI-Caption-8003" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8003
```

腾讯云安全组（控制台操作）：

1. 登录腾讯云控制台 → 云服务器 → 安全组
2. 添加入站规则：TCP 8000 和 8003，来源 0.0.0.0/0，策略允许
3. 确保安全组已关联到服务器实例

> **踩坑**：Windows 防火墙和腾讯云安全组是两道独立的防火墙，只开一个不行，**两个都要开**。

### 第九步：启动服务

```powershell
cd C:\ai-caption-server\main\xiaozhi-server
python app.py
```

看到 `Uvicorn running on http://0.0.0.0:8003` 之类的日志说明启动成功。LLM 的 API key 报错可以忽略，字幕模式不走 LLM。

> **注意**：这个窗口不能关，关了服务就停了。日志里显示的内网 IP（如 10.1.0.8）是自动检测的，不影响实际使用，OTA 接口下发给设备的是配置文件里的公网 IP。

### 第十步：验证

在本地电脑浏览器打开（换成你的公网 IP）：

```
http://你的公网IP:8003/xiaozhi/ota/
```

看到 `OTA接口运行正常，向设备发送的websocket地址是: ws://你的公网IP:8000/xiaozhi/v1/` 就说明部署成功。

> **踩坑**：如果报 502 Bad Gateway，说明服务没在跑。回到服务器检查 PowerShell 窗口是否还开着，`python app.py` 是否还在运行。

## 常见问题

### Q: python 命令找不到

安装 Python 后必须**关闭并重新打开** PowerShell 窗口，PATH 才会刷新。

### Q: git clone 报 Connection was reset

GFW 拦截了 GitHub。用 `gh-proxy.com` 下载 ZIP 替代 git clone。

### Q: ModuleNotFoundError: No module named 'xxx'

依赖没装全。运行 `pip install xxx -i https://pypi.tuna.tsinghua.edu.cn/simple` 单独装缺失的包。

### Q: Could not find Opus library

Windows 缺 opus.dll。按第五步从 NuGet 包 `DSharpPlus.Natives.Opus` 提取 win-x64 版本的 opus.dll 复制到 `C:\Windows\System32\`。

### Q: 检测到 ffmpeg 无法正常运行

Windows 缺 FFmpeg。按第六步从 gyan.dev 下载安装。注意解压后 bin 目录在子目录里，用 `Get-ChildItem -Recurse -Filter ffmpeg.exe` 找到实际路径再加入 PATH。

### Q: HTTP 502 Bad Gateway

服务没在运行。回到服务器检查 `python app.py` 是否还在跑，窗口是否被关了。

### Q: 日志显示内网 IP 而不是公网 IP

日志里的 IP 是 `get_local_ip()` 自动检测的内网地址，不影响实际使用。OTA 接口下发给设备的是配置文件里的公网 IP。访问 `http://公网IP:8003/xiaozhi/ota/` 可以验证实际下发的地址。

### Q: 4核4G 够用吗

够用。字幕模式不加载 LLM/TTS，Python 后端约占 300-500MB 内存，系统约 1.5-2GB，剩余充足。

## 开机自启动（可选）

用任务计划程序：

1. 打开 `taskschd.msc`
2. 创建基本任务 → 名称 "AI字幕后端"
3. 触发器：计算机启动时
4. 操作：启动程序 → `C:\ai-caption-server\main\xiaozhi-server\start-service.bat`
5. 完成

start-service.bat 内容（放在项目根目录）：

```bat
@echo off
title AI字幕设备后端服务
cd /d C:\ai-caption-server\main\xiaozhi-server
:loop
echo [%date% %time%] 启动后端服务...
python app.py
echo [%date% %time%] 服务已停止，5秒后自动重启...
timeout /t 5 /nobreak >nul
goto loop
```

## 文件路径速查

| 用途 | 路径 |
|------|------|
| 后端代码 | C:\ai-caption-server\ |
| 主程序入口 | C:\ai-caption-server\main\xiaozhi-server\app.py |
| 默认配置 | C:\ai-caption-server\main\xiaozhi-server\config.yaml |
| 用户配置 | C:\ai-caption-server\main\xiaozhi-server\data\.config.yaml |
| opus.dll | C:\Windows\System32\opus.dll |
| FFmpeg | C:\ffmpeg\ffmpeg-X.X.X-essentials_build\bin\ |
