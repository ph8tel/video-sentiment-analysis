"""Unit tests for filter_generator.py — no FFmpeg or HTTP required."""

import pytest
from pydantic import ValidationError

from filter_generator import TimelineEntry, build_filter_chain, hex_to_ffmpeg_color


class TestHexToFfmpegColor:
    def test_hash_replaced_with_0x(self):
        assert hex_to_ffmpeg_color("#FF4500").startswith("0x")
        assert "#" not in hex_to_ffmpeg_color("#FF4500")

    def test_lowercase_input_uppercased(self):
        assert hex_to_ffmpeg_color("#ff4500") == "0xFF4500"

    def test_uppercase_input_preserved(self):
        assert hex_to_ffmpeg_color("#FF4500") == "0xFF4500"

    def test_black(self):
        assert hex_to_ffmpeg_color("#000000") == "0x000000"

    def test_white(self):
        assert hex_to_ffmpeg_color("#FFFFFF") == "0xFFFFFF"


class TestBuildFilterChain:
    def _entry(self, start=0.0, end=5.0, score=5, color="#CCCCCC"):
        return TimelineEntry(start=start, end=end, score=score, color=color)

    def test_single_entry_contains_drawbox(self):
        result = build_filter_chain([self._entry()])
        assert "drawbox=" in result

    def test_single_entry_contains_correct_color(self):
        entry = TimelineEntry(start=0.0, end=5.0, score=2, color="#FF4500")
        result = build_filter_chain([entry])
        assert "0xFF4500" in result

    def test_single_entry_contains_timestamps(self):
        entry = TimelineEntry(start=12.4, end=15.8, score=5, color="#CCCCCC")
        result = build_filter_chain([entry])
        assert "between(t,12.4,15.8)" in result

    def test_single_entry_contains_fill(self):
        result = build_filter_chain([self._entry()])
        assert "t=fill" in result

    def test_default_opacity_applied(self):
        result = build_filter_chain([self._entry()])
        assert "@0.70" in result

    def test_custom_opacity_applied(self):
        result = build_filter_chain([self._entry()], opacity=0.5)
        assert "@0.50" in result

    def test_multiple_entries_are_comma_separated(self):
        entries = [
            TimelineEntry(start=0.0, end=3.0, score=6, color="#90EE90"),
            TimelineEntry(start=3.0, end=6.0, score=8, color="#32CD32"),
            TimelineEntry(start=6.0, end=9.0, score=2, color="#FF4500"),
        ]
        result = build_filter_chain(entries)
        assert result.count("drawbox=") == 3
        # Each segment is separated by a comma followed immediately by drawbox
        assert ",drawbox=" in result

    def test_multiple_entries_all_colors_present(self):
        entries = [
            TimelineEntry(start=0.0, end=3.0, score=6, color="#90EE90"),
            TimelineEntry(start=3.0, end=6.0, score=2, color="#FF4500"),
        ]
        result = build_filter_chain(entries)
        assert "0x90EE90" in result
        assert "0xFF4500" in result

    def test_empty_entries_raises(self):
        with pytest.raises(ValueError, match="empty"):
            build_filter_chain([])


class TestTimelineEntryValidation:
    def test_valid_entry_is_created(self):
        entry = TimelineEntry(start=0.0, end=5.0, score=6, color="#90EE90")
        assert entry.start == 0.0
        assert entry.end == 5.0
        assert entry.score == 6

    def test_color_normalized_to_uppercase(self):
        entry = TimelineEntry(start=0.0, end=1.0, score=5, color="#cccccc")
        assert entry.color == "#CCCCCC"

    def test_invalid_color_format_raises(self):
        with pytest.raises(ValidationError):
            TimelineEntry(start=0.0, end=5.0, score=6, color="not-a-color")

    def test_color_without_hash_raises(self):
        with pytest.raises(ValidationError):
            TimelineEntry(start=0.0, end=5.0, score=6, color="FF4500")

    def test_color_wrong_length_raises(self):
        with pytest.raises(ValidationError):
            TimelineEntry(start=0.0, end=5.0, score=6, color="#FFF")

    def test_end_equal_to_start_raises(self):
        with pytest.raises(ValidationError):
            TimelineEntry(start=5.0, end=5.0, score=6, color="#90EE90")

    def test_end_before_start_raises(self):
        with pytest.raises(ValidationError):
            TimelineEntry(start=5.0, end=3.0, score=6, color="#90EE90")

    def test_score_above_max_raises(self):
        with pytest.raises(ValidationError):
            TimelineEntry(start=0.0, end=5.0, score=11, color="#90EE90")

    def test_score_below_min_raises(self):
        with pytest.raises(ValidationError):
            TimelineEntry(start=0.0, end=5.0, score=-1, color="#90EE90")

    def test_score_zero_is_valid(self):
        entry = TimelineEntry(start=0.0, end=1.0, score=0, color="#FF0000")
        assert entry.score == 0

    def test_score_ten_is_valid(self):
        entry = TimelineEntry(start=0.0, end=1.0, score=10, color="#008000")
        assert entry.score == 10

    def test_negative_start_raises(self):
        with pytest.raises(ValidationError):
            TimelineEntry(start=-1.0, end=5.0, score=5, color="#CCCCCC")
