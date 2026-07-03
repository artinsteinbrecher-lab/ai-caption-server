# AI字幕设备后端 — Windows Server 部署指南

基于实际部署经验整理，涵盖腾讯云 Windows Server 上的完整部署流程和踩坑记录。

## 环境信息

- 腾讯云轻量应用服务器 Windows Server，4核4G
- 公网 IP 访问（无域名）
- Python 3.11 + Git + pip 直接部署（不用 Docker、不用 Conda）

## 依赖总览

部署前先了解每个依赖的作用，出问题时方便排查：

| 依赖 | 用途 | 安装方式 |
|------|------|---------|
| Visual C++ 运行库 | torch/onnxruntime 等 C 扩展的运行时依赖 | exe 安装包 |
| Python 3.11 | 运行后端代码 | exe 安装包 |
| Git | 克隆代码仓库 | exe 安装包 |
| torch + torchaudio | SileroVAD 语音活动检测底层框架 | pip 安装（约 2GB） |
| onnxruntime | VAD 模型推理引擎 | pip 安装 |
| opuslib_next + opus.dll | Opus 音频编解码 | pip + 手动复制 DLL |
| FFmpeg | 音频格式转换 | zip 解压 + 加 PATH |
| SileroVAD ONNX 模型 | VAD 推理用的模型文件 | 手动下载 |
| 阿里云百炼 API Key | 实时语音识别服务 | 配置文件填写 |

## 部署步骤

### 第一步：安装 Visual C++ Redistributable

torch、onnxruntime 等 Python 包包含 C 扩展，Windows 上需要 Visual C++ 运行库。如果服务器上没有装过，先装这个：

```powershell
Invoke-WebRequest -Uri "https://aka.ms/vs/17/release/vc_redist.x64.exe" -OutFile "$env:TEMP\vc_redist.x64.exe"
```

```powershell
Start-Process -FilePath "$env:TEMP\vc_redist.x64.exe" -Wait
```

一路下一步即可。装完不需要重启。

> **说明**：如果之前装过 Visual Studio 或其他开发工具，这个运行库可能已经有了。跳过也不会报错——如果后面 pip install torch 时报 "DLL load failed"，再回来装这个。

### 第二步：安装 Python

从华为镜像下载（python.org 在国内很慢）：

```powershell
Invoke-WebRequest -Uri "https://mirrors.huaweicloud.com/python/3.11.9/python-3.11.9-amd64.exe" -OutFile "$env:TEMP\python-installer.exe"
```

```powershell
Start-Process -FilePath "$env:TEMP\python-installer.exe" -Wait
```

安装时**务必勾选** "Add Python to PATH"。

> **踩坑**：安装完成后，当前 PowerShell 窗口的 PATH 不会自动刷新，`python` 命令仍然找不到。必须**关闭当前窗口，重新打开一个新的 PowerShell**。不是新开标签页，是要完全关掉再开。

验证：

```powershell
python --version
```

### 第三步：安装 Git

从 npmmirror 下载：

```powershell
Invoke-WebRequest -Uri "https://registry.npmmirror.com/-/binary/git-for-windows/v2.45.0.windows.1/Git-2.45.0-64-bit.exe" -OutFile "$env:TEMP\git-installer.exe"
```

```powershell
Start-Process -FilePath "$env:TEMP\git-installer.exe" -Wait
```

一路下一步即可。装完**重开 PowerShell**，验证：

```powershell
git --version
```

### 第四步：获取后端代码

```powershell
cd C:\
```

```powershell
git clone https://github.com/artinsteinbrecher-lab/ai-caption-server.git
```

> **踩坑**：国内服务器直连 GitHub 会被 GFW 拦截，报 `Connection was reset`。即使服务器装了 VPN（如 FlClash），git 默认不走系统代理。FlClash 用 TUN 模式时不监听 HTTP 代理端口，`git config --global http.proxy` 也用不了。
>
> **解决方案一**：用 GitHub 代理下载 ZIP：
> ```powershell
> Invoke-WebRequest -Uri "https://gh-proxy.com/https://github.com/artinsteinbrecher-lab/ai-caption-server/archive/refs/heads/master.zip" -OutFile "C:\ai-caption.zip"
> ```
> ```powershell
> Expand-Archive -Path "C:\ai-caption.zip" -DestinationPath "C:\" -Force
> ```
> ```powershell
> Rename-Item "C:\ai-caption-server-master" "C:\ai-caption-server"
> ```
>
> **解决方案二**：ghproxy.net 镜像下载 ZIP：
> ```powershell
> Invoke-WebRequest -Uri "https://ghproxy.net/https://github.com/artinsteinbrecher-lab/ai-caption-server/archive/refs/heads/master.zip" -OutFile "C:\ai-caption.zip"
> ```
>
> **解决方案三**：gitclone.com 镜像（注意对新仓库可能返回空仓库，不推荐）：
> ```powershell
> git clone https://gitclone.com/github.com/artinsteinbrecher-lab/ai-caption-server.git
> ```

### 第五步：安装 Python 依赖

后端项目根目录在 `C:\ai-caption-server\main\xiaozhi-server`。依赖分两批安装：先装 torch（约 2GB，最大最慢），再装其余包。

#### 5.1 安装 torch（单独安装，因为很大）

```powershell
cd C:\ai-caption-server\main\xiaozhi-server
```

```powershell
pip install torch==2.2.2 torchaudio==2.2.2 numpy==1.26.4 -i https://pypi.tuna.tsinghua.edu.cn/simple
```

> **说明**：Windows Server 无 GPU，pip 会自动安装 CPU 版本（约 200MB 下载，安装后约 2GB 磁盘空间）。清华镜像下载速度快很多。如果中途网络断了，重新跑一遍即可，pip 会跳过已下载的包。
>
> **踩坑**：4G 内存的服务器在安装 torch 时可能内存不足导致进程被杀。如果遇到这种情况，先关掉其他占内存的程序（如 FlClash 的多余节点、浏览器等），再重试。实在不行可以尝试 `pip install torch==2.2.2 --no-deps` 先装核心包，再 `pip install numpy` 补依赖。

验证 torch 安装成功：

```powershell
python -c "import torch; print(torch.__version__)"
```

#### 5.2 安装其余依赖

```powershell
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

> **说明**：requirements.txt 里有些包在字幕模式下用不到（如 funasr、edge_tts、modelscope、sherpa_onnx 等），但装上也不影响运行，只是多占点磁盘空间。如果某个包装不上，可以跳过——只要核心包装好了，字幕模式就能跑。
>
> **踩坑**：第一次安装可能不完整，后续启动时会报 `ModuleNotFoundError`。缺什么就单独装什么，比如：
> ```powershell
> pip install aioconsole -i https://pypi.tuna.tsinghua.edu.cn/simple
> ```

#### 5.3 验证关键依赖

逐个检查字幕模式必需的包是否都装好了：

```powershell
python -c "import aiohttp; print('aiohttp OK')"
```

```powershell
python -c "import websockets; print('websockets OK')"
```

```powershell
python -c "import onnxruntime; print('onnxruntime OK')"
```

```powershell
python -c "import opuslib_next; print('opuslib_next OK')"
```

```powershell
python -c "import silero_vad; print('silero_vad OK')"
```

```powershell
python -c "import dashscope; print('dashscope OK')"
```

如果某个报 `ModuleNotFoundError`，单独安装它：

```powershell
pip install 包名 -i https://pypi.tuna.tsinghua.edu.cn/simple
```

> **特别注意 onnxruntime**：SileroVAD 用 onnxruntime 加载模型推理。onnxruntime 可能没有在 requirements.txt 里显式列出，而是作为 sherpa_onnx 的依赖安装。如果 sherpa_onnx 没装成功，onnxruntime 可能也缺失。单独安装：
> ```powershell
> pip install onnxruntime -i https://pypi.tuna.tsinghua.edu.cn/simple
> ```

### 第六步：安装 Opus 音频编解码库

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

验证：

```powershell
python -c "import opuslib_next; print('opus.dll OK')"
```

> **踩坑**：NuGet 包 `opus.win32` 不存在（返回 BlobNotFound），不要用。正确包名是 `DSharpPlus.Natives.Opus`，里面有 win-x64 和 win-arm64 两个版本，用 win-x64。
>
> **备选包名**：如果 `DSharpPlus.Natives.Opus` 下载失败，可以试 `ImeSense.Packages.Opus.Runtimes.win-x64`。

### 第七步：安装 FFmpeg

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

输出类似 `C:\ffmpeg\ffmpeg-8.1.1-essentials_build\bin\ffmpeg.exe`。把这个 bin 目录加入 PATH（把下面的路径换成你实际的）：

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

### 第八步：下载 SileroVAD 模型文件

后端用 SileroVAD 做语音活动检测（判断有没有人说话）。代码通过 onnxruntime 加载 ONNX 模型文件，模型文件路径由 config.yaml 中的 `model_dir: models/snakers4_silero-vad` 指定，完整路径是 `models\snakers4_silero-vad\src\silero_vad\data\silero_vad.onnx`。

需要在项目目录下创建对应文件夹并下载模型：

```powershell
cd C:\ai-caption-server\main\xiaozhi-server
```

```powershell
New-Item -ItemType Directory -Path "models\snakers4_silero-vad\src\silero_vad\data" -Force | Out-Null
```

从 GitHub 下载模型文件（通过 jsdelivr CDN，不受 GFW 影响）：

```powershell
Invoke-WebRequest -Uri "https://cdn.jsdelivr.net/gh/snakers4/silero-vad@master/src/silero_vad/data/silero_vad.onnx" -OutFile "models\snakers4_silero-vad\src\silero_vad\data\silero_vad.onnx"
```

验证文件已下载（应该有 1.8MB 左右）：

```powershell
(Get-Item "models\snakers4_silero-vad\src\silero_vad\data\silero_vad.onnx").Length
```

> **说明**：这个 ONNX 模型文件约 1.8MB。代码期望的完整路径是 `models/snakers4_silero-vad/src/silero_vad/data/silero_vad.onnx`，所以上面创建了好几层目录。
>
> **备选下载方式**：如果 jsdelivr CDN 不通，可以用 gh-proxy.com：
> ```powershell
> Invoke-WebRequest -Uri "https://gh-proxy.com/https://raw.githubusercontent.com/snakers4/silero-vad/master/src/silero_vad/data/silero_vad.onnx" -OutFile "models\snakers4_silero-vad\src\silero_vad\data\silero_vad.onnx"
> ```

### 第九步：创建配置文件

```powershell
cd C:\ai-caption-server\main\xiaozhi-server
```

```powershell
mkdir data -Force
```

```powershell
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

- **公网 IP**：在服务器浏览器打开 https://api.ipify.org 查看
- **API Key**：在 https://bailian.console.aliyun.com/#/api-key 获取

> **注意**：配置文件路径必须是 `data\.config.yaml`（注意文件名以点开头）。系统优先读取此文件，找不到才读 `config.yaml` 默认配置。所以你只需要在 `.config.yaml` 里写覆盖默认值的字段即可。

#### 配置文件字段说明

| 字段 | 说明 |
|------|------|
| `server.websocket` | 设备连接 WebSocket 的地址，必须用公网 IP |
| `server.vision_explain` | 视觉分析接口地址（字幕模式不用，但需配置） |
| `ASR.AliyunBLStreamASR.api_key` | 阿里云百炼 Paraformer 实时语音识别的 API 密钥 |
| `caption_mode` | 设为 true 开启字幕模式（不走 LLM/TTS 回复） |
| `enable_websocket_ping` | WebSocket 心跳保活，建议开启 |

如果需要调整 ASR 参数（如热词、语义断句），在 `.config.yaml` 的 ASR 节补充对应字段即可，参考 `config.yaml` 中 `AliyunBLStreamASR` 的完整配置。

### 第十步：开放防火墙端口

需要开放两个端口：8000（WebSocket）和 8003（HTTP/OTA）。

**Windows 防火墙**（PowerShell 管理员）：

```powershell
New-NetFirewallRule -DisplayName "AI-Caption-8000" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8000
```

```powershell
New-NetFirewallRule -DisplayName "AI-Caption-8003" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8003
```

**腾讯云安全组**（控制台操作）：

1. 登录腾讯云控制台 → 云服务器 → 安全组
2. 添加入站规则：TCP 8000 和 8003，来源 0.0.0.0/0，策略允许
3. 确保安全组已关联到服务器实例

> **踩坑**：Windows 防火墙和腾讯云安全组是两道独立的防火墙，只开一个不行，**两个都要开**。

### 第十一步：启动服务

```powershell
cd C:\ai-caption-server\main\xiaozhi-server
```

```powershell
python app.py
```

看到类似以下日志说明启动成功：

```
OTA接口是        http://10.x.x.x:8003/xiaozhi/ota/
视觉分析接口是    http://10.x.x.x:8003/mcp/vision/explain
Websocket地址是   ws://10.x.x.x:8000/xiaozhi/v1/
```

> **说明**：日志里显示的内网 IP（如 10.1.0.8）是 `get_local_ip()` 自动检测的，不影响实际使用。OTA 接口下发给设备的是配置文件里的公网 IP。
>
> **说明**：LLM 的 API key 报错可以忽略，字幕模式不走 LLM。
>
> **注意**：这个窗口不能关，关了服务就停了。如需后台运行，见下方"开机自启动"。

### 第十二步：验证

在本地电脑浏览器打开（换成你的公网 IP）：

```
http://你的公网IP:8003/xiaozhi/ota/
```

看到 `OTA接口运行正常，向设备发送的websocket地址是: ws://你的公网IP:8000/xiaozhi/v1/` 就说明部署成功。

> **踩坑**：如果报 502 Bad Gateway，说明服务没在跑。回到服务器检查 PowerShell 窗口是否还开着，`python app.py` 是否还在运行。

## 常见问题

### Q: python 命令找不到

安装 Python 后必须**关闭并重新打开** PowerShell 窗口，PATH 才会刷新。不是新开一个标签页，是要完全关掉当前窗口再开。

### Q: pip install torch 报内存不足或进程被杀

4G 内存的服务器装 torch 时可能内存紧张。先关掉其他占内存的程序（FlClash 多余节点、浏览器等），再重试。实在不行用 `pip install torch==2.2.2 --no-deps` 先装核心，再 `pip install numpy` 补依赖。

### Q: pip install 某个包报 "DLL load failed" 或 "Microsoft Visual C++ 14.0 is required"

缺少 Visual C++ 运行库。按第一步安装 Visual C++ Redistributable，然后重新 `pip install`。

### Q: git clone 报 Connection was reset

GFW 拦截了 GitHub。用 `gh-proxy.com` 下载 ZIP 替代 git clone，详见第四步。

### Q: ModuleNotFoundError: No module named 'xxx'

依赖没装全。运行 `pip install xxx -i https://pypi.tuna.tsinghua.edu.cn/simple` 单独装缺失的包。

字幕模式最常缺的包：`aioconsole`、`onnxruntime`、`dashscope`。

### Q: Could not find Opus library / opus.dll 加载失败

Windows 缺 opus.dll。按第六步从 NuGet 包 `DSharpPlus.Natives.Opus` 提取 win-x64 版本的 opus.dll 复制到 `C:\Windows\System32\`。

### Q: 检测到 ffmpeg 无法正常运行

Windows 缺 FFmpeg。按第七步从 gyan.dev 下载安装。注意解压后 bin 目录在子目录里，用 `Get-ChildItem -Recurse -Filter ffmpeg.exe` 找到实际路径再加入 PATH。

### Q: SileroVAD 报模型文件不存在

按第八步下载 SileroVAD ONNX 模型文件。确认文件路径是 `models\snakers4_silero-vad\src\silero_vad\data\silero_vad.onnx`，文件大小约 1.8MB。

### Q: HTTP 502 Bad Gateway

服务没在运行。回到服务器检查 `python app.py` 是否还在跑，窗口是否被关了。

### Q: 日志显示内网 IP 而不是公网 IP

日志里的 IP 是 `get_local_ip()` 自动检测的内网地址，不影响实际使用。OTA 接口下发给设备的是配置文件里的公网 IP。访问 `http://公网IP:8003/xiaozhi/ota/` 可以验证实际下发的地址。

### Q: 4核4G 够用吗

够用。字幕模式不加载 LLM/TTS，Python 后端约占 300-500MB 内存，系统约 1.5-2GB，剩余充足。torch CPU 版约占 2GB 磁盘空间。

## 开机自启动（可选）

用任务计划程序实现开机自动启动 + 崩溃自动重启：

1. 打开 `taskschd.msc`（Win+R 输入 taskschd.msc）
2. 创建基本任务 → 名称 "AI字幕后端"
3. 触发器：计算机启动时
4. 操作：启动程序 → `C:\ai-caption-server\main\xiaozhi-server\start-service.bat`
5. 完成后右键任务 → 属性 → 勾选"不管用户是否登录都要运行"和"使用最高权限运行"

start-service.bat 内容（放在 `C:\ai-caption-server\main\xiaozhi-server\` 下）：

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

> **注意**：.bat 文件必须用 ANSI（GBK）编码保存，不要用 UTF-8。中文 Windows 的 cmd.exe 用 GBK 编码，UTF-8 的 .bat 文件会乱码并把中文当成命令执行。记事本默认保存为 ANSI，直接用记事本编辑即可。

## 文件路径速查

| 用途 | 路径 |
|------|------|
| 后端代码 | C:\ai-caption-server\ |
| 主程序入口 | C:\ai-caption-server\main\xiaozhi-server\app.py |
| 默认配置 | C:\ai-caption-server\main\xiaozhi-server\config.yaml |
| 用户配置 | C:\ai-caption-server\main\xiaozhi-server\data\.config.yaml |
| VAD 模型 | C:\ai-caption-server\main\xiaozhi-server\models\snakers4_silero-vad\src\silero_vad\data\silero_vad.onnx |
| opus.dll | C:\Windows\System32\opus.dll |
| FFmpeg | C:\ffmpeg\ffmpeg-X.X.X-essentials_build\bin\ |
| 启动脚本 | C:\ai-caption-server\main\xiaozhi-server\start-service.bat |
