"""Unit tests for filter_generator.py — no FFmpeg or HTTP required."""

import pytest
from pydantic import ValidationError

from filter_generator import TimelineEntry, build_filter_chain, hex_to_ffmpeg_color, build_filter_graph

from pathlib import Path
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
        assert "@0.7" in result

    def test_custom_opacity_applied(self):
        result = build_filter_chain([self._entry()], opacity=0.5)
        assert "@0.5" in result

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

class TestScoreToTone:
    """score_to_tone maps score integers to tone name strings."""

    @pytest.mark.parametrize("score,expected", [
        (0,  "very_negative"),
        (1,  "very_negative"),
        (2,  "negative"),
        (3,  "slightly_negative"),
        (4,  "slightly_negative"),
        (5,  "neutral"),
        (6,  "slightly_positive"),
        (7,  "slightly_positive"),
        (8,  "positive"),
        (9,  "positive"),
        (10, "very_positive"),
    ])
    def test_score_maps_to_expected_tone(self, score, expected):
        from filter_generator import score_to_tone
        assert score_to_tone(score) == expected

    def test_out_of_range_raises(self):
        from filter_generator import score_to_tone
        with pytest.raises(ValueError):
            score_to_tone(11)


class TestBuildFilterGraph:
    """build_filter_graph returns correct (emoji_paths, filter_complex) pairs."""

    def _make_emoji_dir(self, tmp_path: Path, tones: list[str]) -> Path:
        """Create a fake emoji directory with zero-byte PNG stubs."""
        d = tmp_path / "emoji"
        d.mkdir()
        for tone in tones:
            (d / f"{tone}.png").write_bytes(b"")
        return d

    ALL_TONES = [
        "very_negative", "negative", "slightly_negative", "neutral",
        "slightly_positive", "positive", "very_positive",
    ]

    def _entry(self, start=0.0, end=3.0, score=5, color="#CCCCCC"):
        return TimelineEntry(start=start, end=end, score=score, color=color)

    def test_returns_one_emoji_path_per_entry(self, tmp_path):
        emoji_dir = self._make_emoji_dir(tmp_path, self.ALL_TONES)
        entries = [self._entry(0.0, 3.0, 6), self._entry(3.0, 6.0, 8)]
        paths, _ = build_filter_graph(entries, emoji_dir=emoji_dir)
        assert len(paths) == 2

    def test_emoji_path_matches_tone(self, tmp_path):
        emoji_dir = self._make_emoji_dir(tmp_path, self.ALL_TONES)
        entries = [self._entry(score=0)]  # very_negative
        paths, _ = build_filter_graph(entries, emoji_dir=emoji_dir)
        assert paths[0].name == "very_negative.png"

    def test_filter_complex_contains_boxed_label(self, tmp_path):
        emoji_dir = self._make_emoji_dir(tmp_path, self.ALL_TONES)
        _, fc = build_filter_graph([self._entry()], emoji_dir=emoji_dir)
        assert "[boxed]" in fc

    def test_filter_complex_final_output_labeled_out(self, tmp_path):
        emoji_dir = self._make_emoji_dir(tmp_path, self.ALL_TONES)
        _, fc = build_filter_graph([self._entry()], emoji_dir=emoji_dir)
        assert "[out]" in fc

    def test_filter_complex_single_entry_no_intermediate_labels(self, tmp_path):
        
        emoji_dir = self._make_emoji_dir(tmp_path, self.ALL_TONES)
        _, fc = build_filter_graph([self._entry()], emoji_dir=emoji_dir)
        # With one entry there should be no [s0], [s1] etc — only [boxed] and [out]
        assert "[s0]" not in fc

    def test_filter_complex_multi_entry_intermediate_labels(self, tmp_path):
        emoji_dir = self._make_emoji_dir(tmp_path, self.ALL_TONES)
        entries = [
            self._entry(0.0, 3.0, 6),
            self._entry(3.0, 6.0, 8),
            self._entry(6.0, 9.0, 2),
        ]
        _, fc = build_filter_graph(entries, emoji_dir=emoji_dir)
        assert "[s0]" in fc
        assert "[s1]" in fc
        assert "[s2]" not in fc  # last entry uses [out], not [s2]

    def test_filter_complex_overlay_count_matches_entries(self, tmp_path):
        emoji_dir = self._make_emoji_dir(tmp_path, self.ALL_TONES)
        entries = [self._entry(float(i), float(i + 1), 5) for i in range(4)]
        _, fc = build_filter_graph(entries, emoji_dir=emoji_dir)
        assert fc.count("overlay=") == 4

    def test_filter_complex_contains_timestamps(self, tmp_path):
        emoji_dir = self._make_emoji_dir(tmp_path, self.ALL_TONES)
        entry = TimelineEntry(start=12.4, end=15.8, score=5, color="#CCCCCC")
        _, fc = build_filter_graph([entry], emoji_dir=emoji_dir)
        assert "between(t,12.4,15.8)" in fc

    def test_missing_emoji_png_raises_file_not_found(self, tmp_path):
        emoji_dir = self._make_emoji_dir(tmp_path, ["neutral"])  # only neutral present
        entry = self._entry(score=0)  # needs very_negative.png
        with pytest.raises(FileNotFoundError, match="very_negative.png"):
            build_filter_graph([entry], emoji_dir=emoji_dir)

    def test_empty_entries_raises_value_error(self, tmp_path):
        emoji_dir = self._make_emoji_dir(tmp_path, self.ALL_TONES)
        with pytest.raises(ValueError, match="empty"):
            build_filter_graph([], emoji_dir=emoji_dir)

    def test_custom_emoji_position(self, tmp_path):
        emoji_dir = self._make_emoji_dir(tmp_path, self.ALL_TONES)
        _, fc = build_filter_graph([self._entry()], emoji_dir=emoji_dir, emoji_x=10, emoji_y=20)
        assert "overlay=10:20:" in fc