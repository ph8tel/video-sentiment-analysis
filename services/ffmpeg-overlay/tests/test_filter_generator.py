"""Unit tests for filter_generator.py — no FFmpeg or HTTP required."""

import pytest
from pydantic import ValidationError

from filter_generator import (
    TimelineEntry,
    anger_level_to_emoji,
    build_filter_chain,
    build_filter_graph,
    frustration_level_to_emoji,
    hex_to_ffmpeg_color,
    score_to_tone,
)

from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SENTIMENT_TONES = [
    "very_negative", "negative", "slightly_negative", "neutral",
    "slightly_positive", "positive", "very_positive",
]
ANGER_STEMS      = ["anger_0", "anger_1", "anger_2", "anger_3"]
FRUSTRATION_STEMS = ["frustration_0", "frustration_1", "frustration_2", "frustration_3"]
ALL_STEMS = SENTIMENT_TONES + ANGER_STEMS + FRUSTRATION_STEMS


def make_emoji_dir(tmp_path: Path, stems: list[str]) -> Path:
    """Create a fake emoji directory with zero-byte PNG stubs."""
    d = tmp_path / "emoji"
    d.mkdir(exist_ok=True)
    for stem in stems:
        (d / f"{stem}.png").write_bytes(b"")
    return d


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

    def test_anger_level_defaults_to_zero(self):
        entry = TimelineEntry(start=0.0, end=1.0, score=5, color="#CCCCCC")
        assert entry.anger_level == 0

    def test_frustration_level_defaults_to_zero(self):
        entry = TimelineEntry(start=0.0, end=1.0, score=5, color="#CCCCCC")
        assert entry.frustration_level == 0

    def test_anger_level_three_is_valid(self):
        entry = TimelineEntry(start=0.0, end=1.0, score=5, color="#CCCCCC", anger_level=3)
        assert entry.anger_level == 3

    def test_anger_level_above_3_raises(self):
        with pytest.raises(ValidationError):
            TimelineEntry(start=0.0, end=5.0, score=5, color="#CCCCCC", anger_level=4)

    def test_frustration_level_above_3_raises(self):
        with pytest.raises(ValidationError):
            TimelineEntry(start=0.0, end=5.0, score=5, color="#CCCCCC", frustration_level=4)

    def test_anger_level_below_0_raises(self):
        with pytest.raises(ValidationError):
            TimelineEntry(start=0.0, end=5.0, score=5, color="#CCCCCC", anger_level=-1)

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
        assert score_to_tone(score) == expected

    def test_out_of_range_raises(self):
        with pytest.raises(ValueError):
            score_to_tone(11)


class TestAngerLevelToEmoji:
    @pytest.mark.parametrize("level,expected", [
        (0, "anger_0"),
        (1, "anger_1"),
        (2, "anger_2"),
        (3, "anger_3"),
    ])
    def test_level_maps_to_expected_stem(self, level, expected):
        assert anger_level_to_emoji(level) == expected

    def test_out_of_range_raises(self):
        with pytest.raises(ValueError):
            anger_level_to_emoji(4)


class TestFrustrationLevelToEmoji:
    @pytest.mark.parametrize("level,expected", [
        (0, "frustration_0"),
        (1, "frustration_1"),
        (2, "frustration_2"),
        (3, "frustration_3"),
    ])
    def test_level_maps_to_expected_stem(self, level, expected):
        assert frustration_level_to_emoji(level) == expected

    def test_out_of_range_raises(self):
        with pytest.raises(ValueError):
            frustration_level_to_emoji(4)


class TestBuildFilterGraph:
    """build_filter_graph returns correct (emoji_paths, filter_complex) pairs."""

    def _entry(self, start=0.0, end=3.0, score=5, color="#CCCCCC",
               anger_level=0, frustration_level=0):
        return TimelineEntry(
            start=start, end=end, score=score, color=color,
            anger_level=anger_level, frustration_level=frustration_level,
        )

    def test_returns_three_emoji_paths_per_entry(self, tmp_path):
        emoji_dir = make_emoji_dir(tmp_path, ALL_STEMS)
        entries = [self._entry(0.0, 3.0, 6), self._entry(3.0, 6.0, 8)]
        paths, _ = build_filter_graph(entries, emoji_dir=emoji_dir)
        assert len(paths) == 6  # 3 rows × 2 entries

    def test_sentiment_path_first(self, tmp_path):
        emoji_dir = make_emoji_dir(tmp_path, ALL_STEMS)
        entries = [self._entry(score=0)]  # very_negative
        paths, _ = build_filter_graph(entries, emoji_dir=emoji_dir)
        assert paths[0].name == "very_negative.png"

    def test_anger_path_after_sentiment_paths(self, tmp_path):
        emoji_dir = make_emoji_dir(tmp_path, ALL_STEMS)
        entries = [self._entry(score=5, anger_level=2)]  # neutral sentiment, anger_2
        paths, _ = build_filter_graph(entries, emoji_dir=emoji_dir)
        # paths = [sentiment(0), anger(1), frustration(2)]
        assert paths[1].name == "anger_2.png"

    def test_frustration_path_last(self, tmp_path):
        emoji_dir = make_emoji_dir(tmp_path, ALL_STEMS)
        entries = [self._entry(score=5, frustration_level=3)]
        paths, _ = build_filter_graph(entries, emoji_dir=emoji_dir)
        assert paths[2].name == "frustration_3.png"

    def test_filter_complex_contains_boxed_label(self, tmp_path):
        emoji_dir = make_emoji_dir(tmp_path, ALL_STEMS)
        _, fc = build_filter_graph([self._entry()], emoji_dir=emoji_dir)
        assert "[boxed]" in fc

    def test_filter_complex_final_output_labeled_out(self, tmp_path):
        emoji_dir = make_emoji_dir(tmp_path, ALL_STEMS)
        _, fc = build_filter_graph([self._entry()], emoji_dir=emoji_dir)
        assert "[out]" in fc

    def test_single_entry_has_two_intermediate_labels(self, tmp_path):
        emoji_dir = make_emoji_dir(tmp_path, ALL_STEMS)
        _, fc = build_filter_graph([self._entry()], emoji_dir=emoji_dir)
        # 3 overlays → labels p0, p1, [out]
        assert "[p0]" in fc
        assert "[p1]" in fc
        assert "[p2]" not in fc

    def test_filter_complex_overlay_count_is_three_per_entry(self, tmp_path):
        emoji_dir = make_emoji_dir(tmp_path, ALL_STEMS)
        entries = [self._entry(float(i), float(i + 1), 5) for i in range(4)]
        _, fc = build_filter_graph(entries, emoji_dir=emoji_dir)
        assert fc.count("overlay=") == 12  # 3 rows × 4 entries

    def test_filter_complex_contains_timestamps(self, tmp_path):
        emoji_dir = make_emoji_dir(tmp_path, ALL_STEMS)
        entry = TimelineEntry(start=12.4, end=15.8, score=5, color="#CCCCCC")
        _, fc = build_filter_graph([entry], emoji_dir=emoji_dir)
        # Timestamps appear for every row of overlays
        assert fc.count("between(t,12.4,15.8)") == 3

    def test_sentiment_emoji_at_default_position(self, tmp_path):
        emoji_dir = make_emoji_dir(tmp_path, ALL_STEMS)
        _, fc = build_filter_graph([self._entry()], emoji_dir=emoji_dir)
        assert "overlay=68:68:" in fc

    def test_anger_emoji_at_default_position(self, tmp_path):
        emoji_dir = make_emoji_dir(tmp_path, ALL_STEMS)
        _, fc = build_filter_graph([self._entry()], emoji_dir=emoji_dir)
        assert "overlay=2:202:" in fc

    def test_frustration_emoji_at_default_position(self, tmp_path):
        emoji_dir = make_emoji_dir(tmp_path, ALL_STEMS)
        _, fc = build_filter_graph([self._entry()], emoji_dir=emoji_dir)
        assert "overlay=2:270:" in fc

    def test_custom_sentiment_emoji_position(self, tmp_path):
        emoji_dir = make_emoji_dir(tmp_path, ALL_STEMS)
        _, fc = build_filter_graph([self._entry()], emoji_dir=emoji_dir, emoji_x=10, emoji_y=20)
        assert "overlay=10:20:" in fc

    def test_custom_anger_position(self, tmp_path):
        emoji_dir = make_emoji_dir(tmp_path, ALL_STEMS)
        _, fc = build_filter_graph([self._entry()], emoji_dir=emoji_dir, anger_x=5, anger_y=100)
        assert "overlay=5:100:" in fc

    def test_missing_sentiment_emoji_png_raises_file_not_found(self, tmp_path):
        emoji_dir = make_emoji_dir(tmp_path, ["neutral"])  # only neutral present
        entry = self._entry(score=0)  # needs very_negative.png
        with pytest.raises(FileNotFoundError, match="very_negative.png"):
            build_filter_graph([entry], emoji_dir=emoji_dir)

    def test_missing_anger_emoji_png_raises_file_not_found(self, tmp_path):
        # Provide all sentiment PNGs but no anger PNGs
        emoji_dir = make_emoji_dir(tmp_path, SENTIMENT_TONES)
        entry = self._entry(score=5, anger_level=1)  # needs anger_1.png
        with pytest.raises(FileNotFoundError, match="anger_1.png"):
            build_filter_graph([entry], emoji_dir=emoji_dir)

    def test_missing_frustration_emoji_png_raises_file_not_found(self, tmp_path):
        # Provide sentiment + anger PNGs but no frustration PNGs
        emoji_dir = make_emoji_dir(tmp_path, SENTIMENT_TONES + ANGER_STEMS)
        entry = self._entry(score=5, anger_level=0, frustration_level=2)
        with pytest.raises(FileNotFoundError, match="frustration_2.png"):
            build_filter_graph([entry], emoji_dir=emoji_dir)

    def test_empty_entries_raises_value_error(self, tmp_path):
        emoji_dir = make_emoji_dir(tmp_path, ALL_STEMS)
        with pytest.raises(ValueError, match="empty"):
            build_filter_graph([], emoji_dir=emoji_dir)
