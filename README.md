# AI Caption Server

听障辅助实时字幕设备的后端：接收设备音频 → 阿里云百炼 ASR → 字幕推回设备屏幕。

本项目完全开源（MIT），可以自由修改。配套固件见 [ai-caption-firmware](https://github.com/artinsteinbrecher-lab/ai-caption-firmware)，仓库提供预编译固件，无需自行编译。

## 你需要准备什么

| 项目 | 要求 |
|------|------|
| 运行环境 | 能运行 Python 的电脑或服务器，Windows / Linux 均可 |
| Python | 3.10 及以上（Python 3.11 已实测） |
| 内存 | 最低 1GB 可用，推荐 2GB 以上 |
| 网络 | 能访问 `dashscope.aliyuncs.com:443` |
| 端口 | `8000`（WebSocket，设备连接）、`8003`（HTTP，OTA 配置） |
| 系统依赖 | libopus（Linux：`apt install libopus-dev`；Windows：将 `opus.dll` 放入 `System32`） |
| 阿里云百炼 API Key | 注册阿里云百炼账号获取；个人体验通常可使用免费额度，具体以控制台当前规则为准：[百炼控制台](https://bailian.console.aliyun.com/) |

## 方式 A：个人电脑部署（推荐）

适合设备和电脑在同一个 Wi-Fi。电脑就是后端服务器，电脑关机后字幕服务也会停止。

### 1. 克隆仓库

```bash
git clone --branch master https://github.com/artinsteinbrecher-lab/ai-caption-server.git
cd ai-caption-server
```

### 2. 安装依赖

```bash
python -m pip install -r main/xiaozhi-server/requirements.txt
```

### 3. 创建配置并只修改两行

Linux/macOS：

```bash
cp main/xiaozhi-server/data/.config.yaml.example main/xiaozhi-server/data/.config.yaml
```

Windows PowerShell：

```powershell
Copy-Item main/xiaozhi-server/data/.config.yaml.example main/xiaozhi-server/data/.config.yaml
```

打开 `main/xiaozhi-server/data/.config.yaml`，只改：

1. `server.websocket` 中的 `YOUR_SERVER_HOST`，换成本机局域网 IP；
2. `ASR.AliyunBLStreamASR.api_key`，填入你的阿里云百炼 API Key。

查询本机 IP：Windows 使用 `ipconfig`，Linux 使用 `ip addr` 或 `ifconfig`。

### 4. 启动并验证

```bash
cd main/xiaozhi-server
python app.py
```

浏览器打开 `http://本机IP:8003/xiaozhi/ota/`。看到正常的 OTA 接口响应即表示后端已启动；设备配网时使用同一份配置中的 WebSocket 地址。

## 方式 B：云服务器部署

与个人电脑部署相同：克隆、安装依赖、复制示例配置、启动程序。额外需要：

- 在云防火墙/安全组放行 TCP `8000` 和 `8003`；
- 将 `server.websocket` 改为公网 IP 或域名；
- Windows 使用计划任务，Linux 使用 systemd 或 screen，让服务在后台持续运行。

实测参考：腾讯云轻量 4 核 4G、Windows Server 2019 可以稳定运行。Windows 部署踩坑见 [Windows 部署指南](docs/WINDOWS-DEPLOYMENT-GUIDE.md)。

## 配置说明

示例配置开箱即用，只需改 IP 和 API Key。其余推荐值已经预设并带有注释：

- `caption_mode: true`：纯字幕模式，不进入 LLM/TTS 对话链路；
- `enable_websocket_ping: true`：WebSocket 心跳，降低中间设备断连；
- `close_connection_no_voice_time: 3600`：静音一小时后才关闭普通长连接；
- `semantic_punctuation_enabled: false` + `max_sentence_silence: 900`：低延迟 VAD 断句，优先流式手感；
- `language_hints: ["zh"]`：中文优先，降低误识别为日语的概率。

可选增强：在阿里云百炼控制台创建热词表后配置 `vocabulary_id`，提升人名和专有名词的识别准确率。

partial 字幕默认直发最新完整假设，设备端活动行原地替换；仍保留 120ms 节流、中文过滤、长度限制和 final 去重。需要旧的稳定前缀策略时，可在 ASR 配置中加入 `caption_partial_stable_mode: true`。

## 安全提示

`8000` 端口默认无鉴权。个人局域网部署通常无需额外处理；公网部署建议使用安全组限制来源 IP，或按需开启 `server.auth`。

不要把真实 API Key 写入 Git。运行时配置应使用 `data/.config.yaml`，该文件已被忽略；仓库只提供脱敏的 `.config.yaml.example`。

## 开发者

在仓库根目录执行测试和预检：

```bash
python -m pytest main/xiaozhi-server/tests/ -v
python main/xiaozhi-server/tools/caption_preflight.py
```

协议与改动记录见 [CHANGES-20260823.md](CHANGES-20260823.md)。

本项目基于 [xinnan-tech/xiaozhi-esp32-server](https://github.com/xinnan-tech/xiaozhi-esp32-server) 二次开发，感谢上游项目及其贡献者。
