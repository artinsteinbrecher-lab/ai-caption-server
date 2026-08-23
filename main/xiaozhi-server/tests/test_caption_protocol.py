import unittest

from core.utils.caption import (
    CaptionSequencer,
    build_caption_message,
    caption_metadata,
    caption_segment_id,
    chinese_only_caption,
    finalize_caption,
    limit_caption_text,
    register_final_segment,
    stable_caption_prefix,
)


class CaptionProtocolTest(unittest.TestCase):
    def test_final_caption_adds_chinese_sentence_stop(self):
        self.assertEqual(finalize_caption("今天下午三点开会"), "今天下午三点开会。")

    def test_chinese_only_caption_keeps_mandarin_with_technical_terms(self):
        self.assertEqual(chinese_only_caption(" ESP32-S3 已连接 "), "ESP32-S3 已连接")

    def test_chinese_only_caption_rejects_japanese_kana_and_non_chinese_text(self):
        self.assertEqual(chinese_only_caption("こんにちは"), "")
        self.assertEqual(chinese_only_caption("今日は会議です"), "")
        self.assertEqual(chinese_only_caption("hello world"), "")

    def test_existing_terminal_punctuation_is_preserved(self):
        self.assertEqual(finalize_caption("你到了吗？"), "你到了吗？")

    def test_protocol_metadata_is_explicit_and_legacy_safe(self):
        self.assertEqual(
            caption_metadata("append", True),
            {"version": 2, "action": "append", "final": True},
        )

    def test_v3_metadata_has_stream_and_ordering_fields(self):
        self.assertEqual(
            caption_metadata(
                "partial",
                False,
                version=3,
                stream_id="stream-a",
                segment_id="segment-1",
                seq=7,
                revision=2,
            ),
            {
                "version": 3,
                "action": "partial",
                "final": False,
                "stream_id": "stream-a",
                "segment_id": "segment-1",
                "seq": 7,
                "revision": 2,
            },
        )

    def test_v2_message_keeps_legacy_fields_and_adds_caption_metadata(self):
        payload = build_caption_message("caption-test-session", "今天下午三点开会。", "append", True)
        self.assertEqual(payload["type"], "stt")
        self.assertEqual(payload["text"], "今天下午三点开会。")
        self.assertEqual(payload["session_id"], "caption-test-session")
        self.assertEqual(payload["caption"], {"version": 2, "action": "append", "final": True})

    def test_legacy_message_omits_caption_metadata(self):
        payload = build_caption_message("caption-test-session", "旧后端字幕")
        self.assertEqual(payload["type"], "stt")
        self.assertEqual(payload["text"], "旧后端字幕")
        self.assertEqual(payload["session_id"], "caption-test-session")
        self.assertNotIn("caption", payload)

    def test_v3_message_preserves_metadata_without_changing_legacy_fields(self):
        details = caption_metadata(
            "append", True, version=3, stream_id="s", segment_id="4", seq=9, revision=9
        )
        payload = build_caption_message("caption-test-session", "好的。", caption_details=details)
        self.assertEqual(payload["type"], "stt")
        self.assertEqual(payload["text"], "好的。")
        self.assertEqual(payload["caption"]["seq"], 9)
        self.assertEqual(payload["caption"]["segment_id"], "4")

    def test_partial_caption_is_bounded_without_split_characters(self):
        bounded = limit_caption_text("你好" * 400, max_chars=32)
        self.assertLessEqual(len(bounded), 32)
        self.assertTrue(bounded.startswith("…"))
        self.assertNotIn("\ufffd", bounded)

    def test_caption_sequencer_is_monotonic_and_keeps_segment_until_final(self):
        sequencer = CaptionSequencer("stream-test")
        partial = sequencer.metadata("partial", False, "segment-1")
        repeated_partial = sequencer.metadata("partial", False, "segment-1")
        final = sequencer.metadata("append", True, "segment-1")
        next_segment = sequencer.metadata("partial", False)
        self.assertEqual(partial["seq"], 1)
        self.assertEqual(repeated_partial["seq"], 2)
        self.assertEqual(final["seq"], 3)
        self.assertEqual(next_segment["seq"], 4)
        self.assertEqual(next_segment["segment_id"], "2")
        self.assertEqual(final["stream_id"], "stream-test")

    def test_segment_id_falls_back_to_provider_timestamps(self):
        self.assertEqual(caption_segment_id({"sentence_id": 7}), "id:7")
        self.assertEqual(
            caption_segment_id({"begin_time": 120, "end_time": 980}),
            "time:120:980",
        )

    def test_final_segment_registration_rejects_exact_duplicate(self):
        seen = set()
        self.assertTrue(register_final_segment(seen, "time:120:980"))
        self.assertFalse(register_final_segment(seen, "time:120:980"))
        self.assertTrue(register_final_segment(seen, "time:1000:1500"))

    def test_stable_caption_prefix_only_returns_adjacent_agreement(self):
        self.assertEqual(stable_caption_prefix("今天下午", "今天下午三点"), "今天下午")
        self.assertEqual(stable_caption_prefix("今天下午", "明天下午"), "")


if __name__ == "__main__":
    unittest.main()
