"""Offline preflight for the caption server configuration.

This command never contacts a server and never prints credentials.  It is
intended to catch configuration drift before a human-approved deployment.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config(default_path: Path, override_path: Path | None) -> dict[str, Any]:
    with default_path.open(encoding="utf-8") as handle:
        config = yaml.safe_load(handle) or {}
    if override_path and override_path.exists():
        with override_path.open(encoding="utf-8") as handle:
            config = _deep_merge(config, yaml.safe_load(handle) or {})
    return config


def check_config(config: dict[str, Any]) -> list[str]:
    asr_name = config.get("selected_module", {}).get("ASR", "AliyunBLStreamASR")
    asr = config.get("ASR", {}).get(asr_name, {})
    caption = config.get("caption", {})
    issues: list[str] = []
    if config.get("caption_mode") is not True:
        issues.append("caption_mode must be true")
    if int(caption.get("protocol_version", 0)) < 3:
        issues.append("caption.protocol_version must be >= 3")
    if "zh" not in (asr.get("language_hints") or []):
        issues.append("ASR.language_hints must include zh")
    if asr.get("semantic_punctuation_enabled") is not True:
        issues.append("ASR.semantic_punctuation_enabled must be true")
    if int(asr.get("max_sentence_silence", 0)) < 500:
        issues.append("ASR.max_sentence_silence should be >= 500ms for readable Chinese captions")
    if asr.get("multi_threshold_mode_enabled") is not True:
        issues.append("ASR.multi_threshold_mode_enabled must be true")
    websocket = config.get("server", {}).get("websocket", "")
    if websocket and "YOUR_SERVER_HOST" in websocket:
        issues.append("server.websocket is still a placeholder")
    if config.get("server", {}).get("auth", {}).get("enabled") is not True:
        issues.append("WARNING: server.auth.enabled is false; confirm network controls before deployment")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("config.yaml"))
    parser.add_argument("--override", type=Path, default=Path("data/.config.yaml"))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    config = load_config(args.config, args.override if args.override.exists() else None)
    issues = check_config(config)
    result = {"ok": not any(not item.startswith("WARNING:") for item in issues), "issues": issues}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("caption preflight: " + ("PASS" if result["ok"] else "FAIL"))
        for issue in issues:
            print("- " + issue)
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
