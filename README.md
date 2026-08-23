# AI字幕辅助设备 — 后端

基于 [xiaozhi-esp32-server](https://github.com/xinnan-tech/xiaozhi-esp32-server) 完整源码修改的实时语音转字幕设备后端服务，专为听障人士设计的辅助工具。

## 项目简介

本项目在原版小智后端基础上进行修改，去除了 AI 对话、LLM、TTS 等功能链路，只保留：接收设备音频流 → 调用阿里云百炼 Paraformer 实时 ASR → 流式返回识别文本 → 推送字幕到设备屏幕显示。

## 修改文件清单

| 文件 | 修改内容 |
|------|----------|
| `main/xiaozhi-server/config.yaml` | 启用 `enable_websocket_ping`（防止 NAT/防火墙静默断开）；`caption_mode` 只保留顶层定义，删除 ASR 节中的重复定义 |
| `main/xiaozhi-server/core/handle/receiveAudioHandle.py` | caption 模式下静音超时直接关闭连接，不触发 AI 对话流程（避免结束语被当作字幕显示） |
| `main/xiaozhi-server/core/providers/asr/aliyunbl_stream.py` | vocabulary_id 空值保护、forward_task 取消防竞态、is_final 结果跳过去重、caption_mode 改读 conn.config、ASR 异常时通知设备显示 |
| `main/xiaozhi-server/core/utils/caption.py` | 中文输出门槛、活动句稳定处理、定稿去重、caption 序列元数据 |
| `main/xiaozhi-server/core/handle/sendAudioHandle.py` | 保留旧版 `stt.text`，按需附加 `caption.action/stream_id/segment_id/seq` |
| `main/xiaozhi-server/tests/test_caption_protocol.py` | 新旧字幕协议、中文过滤、去重和序列一致性测试 |
| `main/xiaozhi-server/tools/caption_preflight.py` | 启动前配置与依赖检查 |

## 关键修复

### P0 修复

- **静音超时连接泄漏 + 结束语被当作字幕显示**：原版静音超时后会调用 `startToChat()` 触发 AI 对话，在 caption 模式下这会导致 AI 的结束语被当作字幕显示在屏幕上。修复后 caption 模式直接关闭连接

### P1 修复

- **vocabulary_id 为 null 时仍发送到阿里云 API**：增加空值判断
- **forward_task 未取消导致竞态**：`_cleanup()` 开头先 cancel 并 await forward_task
- **caption_last_text 去重丢失最终结果**：对 `is_final` 的结果总是发送
- **caption_mode 双重定义**：ASR Provider 改为通过 `conn.config.get("caption_mode")` 读取
- **ASR 异常无设备反馈**：task-failed 时发送 `[识别异常，正在恢复...]` 到设备
- **中间字幕叠加**：`partial` 只替换活动句，只有 `append` 才进入历史，避免同一句话产生多行重复字幕
- **误识别日语**：配置优先使用 `language_hints: ["zh"]`，服务端再执行中文输出门槛

## 部署方法

### 方式一：Docker 部署（推荐）

```bash
# 1. 修改配置
cp main/xiaozhi-server/config.yaml main/xiaozhi-server/config_from_api.yaml
# 编辑 config_from_api.yaml，填入你的阿里云百炼 API Key

# 2. Docker Compose 启动
cd main/xiaozhi-server
docker-compose up -d
```

### 方式二：手动部署

```bash
cd main/xiaozhi-server
pip install -r requirements.txt

# 编辑 config.yaml，填入：
# - 阿里云百炼 API Key（ASR 识别用）
# - caption_mode: true（顶层配置，约第 254 行）
# - enable_websocket_ping: true（约第 75 行）

python app.py
```

> **Windows Server 部署**：如果你在 Windows Server 上手动部署，请参阅 [Windows Server 部署指南](docs/WINDOWS-DEPLOYMENT-GUIDE.md)（含 opus.dll 安装、FFmpeg 配置、腾讯云安全组等踩坑记录）。

### 关键配置项

| 配置项 | 位置 | 值 | 说明 |
|--------|------|-----|------|
| `caption_mode` | 顶层 | `true` | 启用字幕模式 |
| `enable_websocket_ping` | 顶层（约第 75 行） | `true` | 防止长连接被 NAT 断开 |
| `close_connection_no_voice_time` | 顶层 | `3600` | 长连接空闲保护 |
| `api_key` | ASR 配置节 | 你的阿里云百炼 API Key | 语音识别用 |
| `model` | ASR 配置节 | `paraformer-realtime-v2` | 阿里云实时 ASR 模型 |
| `language_hints` | ASR 配置节 | `["zh"]` | 中文优先，降低误识别日语 |
| `semantic_punctuation_enabled` | ASR 配置节 | `false` | VAD 断句，优先流式手感 |
| `max_sentence_silence` | ASR 配置节 | `900` | VAD 静音断句阈值（毫秒） |

## 配套固件

固件代码请见：[ai-caption-firmware](https://github.com/artinsteinbrecher-lab/ai-caption-firmware)

## 使用文档

详细使用手册（含服务端搭建、固件烧录、故障排查）请见：[ai-caption](https://github.com/artinsteinbrecher-lab/ai-caption)

Windows Server 部署指南（含踩坑记录）请见：[Windows Server 部署指南](docs/WINDOWS-DEPLOYMENT-GUIDE.md)

## 致谢

基于以下开源项目修改：
- [xinnan-tech/xiaozhi-esp32-server](https://github.com/xinnan-tech/xiaozhi-esp32-server) — 小智 ESP32 后端服务
