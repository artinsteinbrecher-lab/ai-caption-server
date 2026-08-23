"""Small, dependency-free helpers for the caption-only transport protocol."""

from typing import Dict, Optional
from uuid import uuid4


_TERMINAL_PUNCTUATION = "。！？!?；;：:…"


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
