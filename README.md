# AI 实时字幕设备 — 后端服务

> 配套固件：[ai-caption-firmware](https://github.com/artinsteinbrecher-lab/ai-caption-firmware)

接收设备音频 → 阿里云百炼 Paraformer ASR → 推送字幕文字回设备屏幕

---

## 部署方法

详细部署步骤请见固件仓库的文档：

**→ [完整部署文档](https://github.com/artinsteinbrecher-lab/ai-caption-firmware/blob/main/docs/02-server-deploy.md)**

---

## 快速配置

部署完成后，编辑 `main/xiaozhi-server/data/.config.yaml`：

```yaml
server:
  websocket: ws://你的服务器IP:8000/xiaozhi/v1/
  vision_explain: http://你的服务器IP:8003/mcp/vision/explain

ASR:
  AliyunBLStreamASR:
    api_key: sk-你的阿里云百炼APIKey
    model: paraformer-realtime-v2

caption_mode: true
enable_websocket_ping: true
```

---

## 启动服务

```bash
cd main/xiaozhi-server
python app.py
```

验证是否正常：浏览器访问 `http://服务器IP:8003/xiaozhi/ota/`，看到"OTA接口运行正常"即成功。

---

## 需要开放的端口

| 端口 | 用途 |
|------|------|
| `8000` | WebSocket（设备连接） |
| `8003` | HTTP OTA（设备配置） |

---

## 修改内容说明

本项目基于 [xiaozhi-esp32-server](https://github.com/xinnan-tech/xiaozhi-esp32-server) 修改，主要改动：

- `core/handle/receiveAudioHandle.py`：caption 模式静音超时直接关闭连接
- `core/providers/asr/aliyunbl_stream.py`：流式 ASR 稳定性修复
- `config.yaml`：启用 `caption_mode` 和 `enable_websocket_ping`

---

## Windows Server 部署

参见 [docs/WINDOWS-DEPLOYMENT-GUIDE.md](docs/WINDOWS-DEPLOYMENT-GUIDE.md)
