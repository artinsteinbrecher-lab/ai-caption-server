# AI Caption Server

面向听障人士的辅助字幕设备后端：接收设备音频 → 调用阿里云百炼实时 ASR → 将字幕流式推送回设备。

本项目是纯字幕模式后端，不走 LLM、TTS 或普通 AI 对话链路。设备端负责把 `partial` 活动句原地替换，把 `append` 定稿句换行显示。

## 端口

| 端口 | 协议/用途 | 说明 |
|------|-----------|------|
| `8000` | WebSocket | 设备连接、音频上传和字幕下发 |
| `8003` | HTTP | OTA 配置接口 `/xiaozhi/ota/` 与视觉接口 |

## 三步部署

### 1. 克隆并安装依赖

```bash
git clone --branch master https://github.com/artinsteinbrecher-lab/ai-caption-server.git
cd ai-caption-server/main/xiaozhi-server
python -m pip install -r requirements.txt
```

### 2. 创建运行时配置

在 `main/xiaozhi-server` 目录执行：

```bash
cp data/.config.yaml.example data/.config.yaml
```

只需要修改两处：

1. `server.websocket`：把 `YOUR_SERVER_HOST` 改成设备可访问的服务器 IP 或域名，端口保持 `8000`。
2. `ASR.AliyunBLStreamASR.api_key`：填入阿里云百炼 API Key。

### 3. 启动并验证

```bash
python app.py
```

浏览器打开 `http://YOUR_SERVER_HOST:8003/xiaozhi/ota/`。能够访问 OTA 接口后，将同一个 WebSocket 地址提供给设备配网使用。

## 推荐配置

示例配置已经包含以下现网验证过的值：

| 配置项 | 推荐值 | 含义 |
|--------|--------|------|
| `caption_mode` | `true` | 启用纯字幕模式，不进入 LLM/TTS 对话链路 |
| `enable_websocket_ping` | `true` | 启用 WebSocket 心跳，降低 NAT 或防火墙断连概率 |
| `close_connection_no_voice_time` | `3600` | 无语音时的长连接保护时间（秒） |
| `semantic_punctuation_enabled` | `false` | 使用 VAD 断句，优先保证逐字流式手感 |
| `max_sentence_silence` | `900` | VAD 静音断句阈值，单位毫秒 |
| `language_hints` | `["zh"]` | 优先中文识别，降低误识别为日语的概率 |

`partial` 默认直发最新完整假设，设备端活动行会原地替换；保留 120ms 发送节流、中文过滤、长度限制和 final 去重。若需要旧的稳定前缀策略，可在 ASR 配置中增加 `caption_partial_stable_mode: true`。

## 部署建议

- `8000` 默认没有鉴权。公网部署时，建议通过防火墙限制来源，或按需开启 `server.auth`。
- 专有名词较多时，可以在阿里云百炼控制台创建热词表，再配置 `vocabulary_id`。
- Windows Server 部署踩坑和排查方法见 [Windows 部署指南](docs/WINDOWS-DEPLOYMENT-GUIDE.md)。

## 开发与验证

在仓库根目录执行：

```bash
python -m pytest main/xiaozhi-server/tests/ -v
python main/xiaozhi-server/tools/caption_preflight.py
```

本轮改动记录见 [CHANGES-20260823.md](CHANGES-20260823.md)。核心协议实现位于 `main/xiaozhi-server/core/utils/caption.py`，ASR 流式实现位于 `main/xiaozhi-server/core/providers/asr/aliyunbl_stream.py`。

## 配套项目

- 固件：[ai-caption-firmware](https://github.com/artinsteinbrecher-lab/ai-caption-firmware)
- 设备端说明：[ai-caption](https://github.com/artinsteinbrecher-lab/ai-caption)

## 致谢

本项目基于上游 [xinnan-tech/xiaozhi-esp32-server](https://github.com/xinnan-tech/xiaozhi-esp32-server) 修改，感谢上游项目及其贡献者。
