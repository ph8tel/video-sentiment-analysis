"""Unit tests for color_mapper.py — no I/O, no mocking required."""

import pytest

from color_mapper import (
    Tone,
    TONE_MAP,
    resolve_tie,
    score_to_tone,
    tone_to_color,
)


class TestToneMap:
    def test_all_seven_tones_present(self):
        assert len(TONE_MAP) == 7
        for tone in Tone:
            assert tone in TONE_MAP

    def test_scores_are_correct(self):
        expected = {
            Tone.VERY_NEGATIVE:     0,
            Tone.NEGATIVE:          2,
            Tone.SLIGHTLY_NEGATIVE: 3,
            Tone.NEUTRAL:           5,
            Tone.SLIGHTLY_POSITIVE: 6,
            Tone.POSITIVE:          8,
            Tone.VERY_POSITIVE:     10,
        }
        for tone, score in expected.items():
            assert TONE_MAP[tone].score == score

    def test_colors_are_correct(self):
        expected = {
            Tone.VERY_NEGATIVE:     "#FF0000",
            Tone.NEGATIVE:          "#FF4500",
            Tone.SLIGHTLY_NEGATIVE: "#FFA500",
            Tone.NEUTRAL:           "#CCCCCC",
            Tone.SLIGHTLY_POSITIVE: "#90EE90",
            Tone.POSITIVE:          "#32CD32",
            Tone.VERY_POSITIVE:     "#008000",
        }
        for tone, color in expected.items():
            assert TONE_MAP[tone].hex_color == color

    def test_scores_are_monotonically_increasing(self):
        scores = [info.score for info in TONE_MAP.values()]
        assert scores == sorted(scores)


class TestToneToColor:
    def test_returns_hex_string(self):
        assert tone_to_color(Tone.NEUTRAL) == "#CCCCCC"

    def test_all_tones_return_non_empty_color(self):
        for tone in Tone:
            color = tone_to_color(tone)
            assert color.startswith("#")
            assert len(color) == 7


class TestScoreToTone:
    def test_exact_score_very_negative(self):
        assert score_to_tone(0) == Tone.VERY_NEGATIVE

    def test_exact_score_negative(self):
        assert score_to_tone(2) == Tone.NEGATIVE

    def test_exact_score_slightly_negative(self):
        assert score_to_tone(3) == Tone.SLIGHTLY_NEGATIVE

    def test_exact_score_neutral(self):
        assert score_to_tone(5) == Tone.NEUTRAL

    def test_exact_score_slightly_positive(self):
        assert score_to_tone(6) == Tone.SLIGHTLY_POSITIVE

    def test_exact_score_positive(self):
        assert score_to_tone(8) == Tone.POSITIVE

    def test_exact_score_very_positive(self):
        assert score_to_tone(10) == Tone.VERY_POSITIVE

    def test_score_closer_to_negative_than_very_negative(self):
        # 1.5 is closer to 2 (NEGATIVE) than to 0 (VERY_NEGATIVE)
        assert score_to_tone(1.5) == Tone.NEGATIVE

    def test_score_closer_to_neutral_than_slightly_negative(self):
        # 4.5 is closer to 5 (NEUTRAL) than to 3 (SLIGHTLY_NEGATIVE)
        assert score_to_tone(4.5) == Tone.NEUTRAL

    def test_score_closer_to_positive_than_slightly_positive(self):
        # 7.5 is closer to 8 (POSITIVE) than to 6 (SLIGHTLY_POSITIVE)
        assert score_to_tone(7.5) == Tone.POSITIVE

    def test_float_overall_score(self):
        result = score_to_tone(5.67)
        assert isinstance(result, Tone)

    # --- tie points (equidistant between two adjacent tones) ---

    def test_tie_at_1_resolves_to_lower(self):
        # 1 is equidistant between VERY_NEGATIVE(0) and NEGATIVE(2)
        assert score_to_tone(1) == Tone.VERY_NEGATIVE

    def test_tie_at_4_resolves_to_lower(self):
        # 4 is equidistant between SLIGHTLY_NEGATIVE(3) and NEUTRAL(5)
        assert score_to_tone(4) == Tone.SLIGHTLY_NEGATIVE

    def test_tie_at_7_resolves_to_lower(self):
        # 7 is equidistant between SLIGHTLY_POSITIVE(6) and POSITIVE(8)
        assert score_to_tone(7) == Tone.SLIGHTLY_POSITIVE

    def test_tie_at_9_resolves_to_lower(self):
        # 9 is equidistant between POSITIVE(8) and VERY_POSITIVE(10)
        assert score_to_tone(9) == Tone.POSITIVE


class TestResolveTie:
    """
    Tests for the tie-breaking stub.

    These tests pin the *current* behaviour (return lower-scoring tone) and
    serve as the acceptance criteria when the correction logic is implemented.
    Replacing resolve_tie() with a smarter strategy should make these tests
    the first thing to update.
    """

    def test_returns_lower_scoring_of_two_candidates(self):
        result = resolve_tie([Tone.POSITIVE, Tone.VERY_POSITIVE], 9.0)
        assert result == Tone.POSITIVE

    def test_returns_lower_scoring_on_negative_side(self):
        result = resolve_tie([Tone.VERY_NEGATIVE, Tone.NEGATIVE], 1.0)
        assert result == Tone.VERY_NEGATIVE

    def test_single_candidate_returned_unchanged(self):
        result = resolve_tie([Tone.NEUTRAL], 5.0)
        assert result == Tone.NEUTRAL

    def test_receives_original_score_as_context(self):
        # score is passed so future implementations can use it for
        # model re-scoring or windowing; verify it doesn't break anything now
        result = resolve_tie([Tone.SLIGHTLY_POSITIVE, Tone.POSITIVE], 7.0)
        assert result == Tone.SLIGHTLY_POSITIVE

    def test_order_of_candidates_does_not_affect_result(self):
        # resolve_tie must not depend on list order
        a = resolve_tie([Tone.POSITIVE, Tone.VERY_POSITIVE], 9.0)
        b = resolve_tie([Tone.VERY_POSITIVE, Tone.POSITIVE], 9.0)
        assert a == b == Tone.POSITIVE
