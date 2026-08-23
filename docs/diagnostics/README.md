# 后端诊断资料归档

本目录用于保存经过脱敏的后端诊断材料，建议按以下方式归档：

- `server-YYYYMMDD.log.txt`：只保留连接、ASR、字幕下发和清理相关行。
- `config-effective-YYYYMMDD.yaml`：只保留字段名和非敏感值，所有 `api_key`、`token`、`secret`、`password` 打码。
- `timeline-YYYYMMDD.md`：记录设备连接、首字延迟、句末定稿和静音清理时间线。

当前本机源码目录没有后端运行时日志文件，故本次不添加虚构日志。`tmp/`、原始日志和运行时配置均由 Git 忽略，避免把密钥、设备地址或音频识别内容上传到公开仓库。
