"""Small, dependency-free helpers for the caption-only transport protocol."""

import re
from typing import Dict, Mapping, MutableSet, Optional
from uuid import uuid4


_TERMINAL_PUNCTUATION = "。！？!?；;：:…"

# Aliyun's language hint makes Mandarin the preferred recognition language, but
# it is not an output guarantee.  Japanese normally includes kana, which is
# unambiguous and should never reach a Chinese-only caption device.  A result
# also needs at least one Han character: empty, English-only, Korean, Cyrillic
# and other non-Chinese hypotheses are not useful captions for this product.
_HAN_CHARACTER = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
_NON_CHINESE_SCRIPT = re.compile(
    r"[\u3040-\u30ff\u31f0-\u31ff\uff66-\uff9f\uac00-\ud7af\u0400-\u052f]"
)


def chinese_only_caption(text: str) -> str:
    """Return a display-safe Chinese caption, or an empty string when rejected.

    This is intentionally a narrow output gate, not a second ASR engine.  It
    preserves numbers and ASCII terms inside a Chinese sentence (for example,
    ``ESP32-S3``), but blocks Japanese kana and any result without Han text.
    Japanese made only of Han characters cannot be distinguished reliably from
    Chinese without a language classifier; the upstream ``language_hints``
    remains the first line of defence for that edge case.
    """
    normalized = (text or "").strip()
    if not normalized:
        return ""
    if _NON_CHINESE_SCRIPT.search(normalized):
        return ""
    if not _HAN_CHARACTER.search(normalized):
        return ""
    return normalized


def stable_caption_prefix(previous: str, current: str, min_chars: int = 1) -> str:
    """Return the prefix shared by adjacent ASR hypotheses.

    Streaming ASR commonly revises the last few characters.  Showing only the
    shared prefix prevents those revisions from making the display flicker.
    The final ASR packet is still sent in full by the provider.
    """
    previous = previous or ""
    current = current or ""
    size = 0
    for left, right in zip(previous, current):
        if left != right:
            break
        size += 1
    if size < max(0, min_chars):
        return ""
    return current[:size]


def caption_segment_id(sentence: Mapping[str, object]) -> Optional[str]:
    """Return a stable provider segment key suitable for final de-duplication.

    Aliyun responses do not always include ``sentence_id``. Final packets do,
    however, carry timing metadata, so use it as a deterministic fallback.
    """
    provider_id = sentence.get("sentence_id") or sentence.get("id")
    if provider_id is not None:
        return f"id:{provider_id}"

    begin_time = sentence.get("begin_time")
    end_time = sentence.get("end_time")
    if begin_time is not None or end_time is not None:
        return f"time:{begin_time if begin_time is not None else ''}:{end_time if end_time is not None else ''}"
    return None


def register_final_segment(
    seen: MutableSet[str], segment_id: Optional[str], max_entries: int = 512
) -> bool:
    """Register a final segment and return ``False`` for an exact duplicate.

    The set is deliberately bounded because caption connections can remain
    open for many hours. Clearing an old window is safe: very old provider
    packets are independently rejected by the device's monotonic sequence.
    """
    if segment_id is None:
        return True
    if segment_id in seen:
        return False
    if max_entries > 0 and len(seen) >= max_entries:
        seen.clear()
    seen.add(segment_id)
    return True


class CaptionSequencer:
    """Allocate monotonic v3 caption metadata for one ASR stream."""

    def __init__(self, stream_id: Optional[str] = None):
        self.stream_id = stream_id or uuid4().hex
        self.seq = 0
        self.next_segment_id = 1
        self.active_segment_id: Optional[str] = None

    def metadata(
        self,
        action: str,
        is_final: bool,
        segment_id: Optional[str] = None,
    ) -> Dict[str, object]:
        if segment_id is None:
            segment_id = self.active_segment_id
        if segment_id is None:
            segment_id = str(self.next_segment_id)
            self.next_segment_id += 1
        elif is_final:
            # Keep fallback IDs from colliding after providers supply their own
            # sentence identifiers.
            self.next_segment_id += 1
        self.active_segment_id = None if is_final else segment_id
        self.seq += 1
        return caption_metadata(
            action,
            is_final,
            version=3,
            stream_id=self.stream_id,
            segment_id=segment_id,
            seq=self.seq,
            revision=self.seq,
        )


def limit_caption_text(text: str, max_chars: int = 512) -> str:
    """Bound an active caption without splitting UTF-8 characters."""
    normalized = text.strip()
    if max_chars <= 0 or len(normalized) <= max_chars:
        return normalized
    return "…" + normalized[-(max_chars - 1):]


def finalize_caption(text: str) -> str:
    """Return a readable, sentence-complete subtitle without rewriting ASR text."""
    normalized = text.strip()
    if normalized and normalized[-1] not in _TERMINAL_PUNCTUATION:
        normalized += "。"
    return normalized


def caption_metadata(
    action: str,
    is_final: bool,
    *,
    version: int = 2,
    stream_id: Optional[str] = None,
    segment_id: Optional[str] = None,
    seq: Optional[int] = None,
    revision: Optional[int] = None,
) -> Dict[str, object]:
    """Build caption metadata while keeping v2 as the compatibility default."""
    metadata: Dict[str, object] = {
        "version": version,
        "action": action,
        "final": is_final,
    }
    if stream_id is not None:
        metadata["stream_id"] = stream_id
    if segment_id is not None:
        metadata["segment_id"] = segment_id
    if seq is not None:
        metadata["seq"] = seq
    if revision is not None:
        metadata["revision"] = revision
    return metadata


def build_caption_message(
    session_id: str,
    text: str,
    caption_action: str = None,
    is_final: bool = False,
    caption_details: Optional[Dict[str, object]] = None,
) -> Dict[str, object]:
    """Build an STT payload while preserving the legacy wire contract."""
    message = {"type": "stt", "text": text, "session_id": session_id}
    if caption_details is not None:
        message["caption"] = dict(caption_details)
    elif caption_action:
        message["caption"] = caption_metadata(caption_action, is_final)
    return message
