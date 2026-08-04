from merge import assign_speaker, merge_transcript_with_speakers


def test_merge_assigns_speaker_by_max_overlap(sample_whisper_segments, sample_diarization):
    chunks, speaker_order = merge_transcript_with_speakers(
        sample_whisper_segments, sample_diarization["complete"]
    )

    assert [c["speaker"] for c in chunks] == ["SPEAKER_00", "SPEAKER_01", "SPEAKER_00"]
    assert speaker_order == ["SPEAKER_00", "SPEAKER_01"]
    # original transcript fields are preserved
    assert chunks[0]["text"] == sample_whisper_segments[0]["text"]
    assert chunks[0]["start"] == sample_whisper_segments[0]["start"]


def test_merge_preserves_chronological_order():
    segments = [
        {"start": 0.0, "end": 1.0, "text": "a"},
        {"start": 1.0, "end": 2.0, "text": "b"},
    ]
    turns = [
        {"start": 0.0, "end": 1.0, "speaker": "SPEAKER_01"},
        {"start": 1.0, "end": 2.0, "speaker": "SPEAKER_00"},
    ]
    chunks, speaker_order = merge_transcript_with_speakers(segments, turns)
    assert speaker_order == ["SPEAKER_01", "SPEAKER_00"]
    assert chunks[0]["speaker"] == "SPEAKER_01"
    assert chunks[1]["speaker"] == "SPEAKER_00"


def test_assign_speaker_falls_back_to_nearest_turn_on_gap():
    # Segment falls entirely within a silent gap between two turns.
    segment = {"start": 10.0, "end": 10.5, "text": "..."}
    turns = [
        {"start": 0.0, "end": 5.0, "speaker": "SPEAKER_00"},
        {"start": 12.0, "end": 15.0, "speaker": "SPEAKER_01"},
    ]
    assert assign_speaker(segment, turns) == "SPEAKER_01"


def test_assign_speaker_returns_none_with_no_turns():
    segment = {"start": 0.0, "end": 1.0, "text": "hello"}
    assert assign_speaker(segment, []) is None


def test_merge_falls_back_to_unknown_with_no_turns():
    segments = [{"start": 0.0, "end": 1.0, "text": "hello"}]
    chunks, speaker_order = merge_transcript_with_speakers(segments, [])
    assert chunks[0]["speaker"] == "UNKNOWN"
    assert speaker_order == ["UNKNOWN"]
