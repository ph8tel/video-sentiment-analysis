import subprocess

import httpx
import pytest

import clients


@pytest.fixture(scope="session")
def tiny_video_bytes(tmp_path_factory):
    """Generate a 1-second 320x240 black MP4 via FFmpeg's lavfi source."""
    out = tmp_path_factory.mktemp("video") / "tiny.mp4"
    result = subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "color=c=black:s=320x240:d=1:r=10",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
            "-c:v", "libx264", "-c:a", "aac", "-pix_fmt", "yuv420p",
            str(out),
        ],
        capture_output=True,
    )
    if result.returncode != 0:
        pytest.skip("FFmpeg not available — skipping ingest API tests")
    return out.read_bytes()


def test_ingest_merges_whisper_and_pyannote_results(
    client, tiny_video_bytes, sample_whisper_segments, sample_diarization, monkeypatch
):
    async def fake_call_whisper(audio_bytes, filename="audio.wav"):
        return {"text": "...", "segments": sample_whisper_segments}

    async def fake_call_pyannote(audio_bytes, num_speakers, filename="audio.wav"):
        assert num_speakers == 2
        return sample_diarization

    monkeypatch.setattr(clients, "call_whisper", fake_call_whisper)
    monkeypatch.setattr(clients, "call_pyannote", fake_call_pyannote)

    response = client.post(
        "/ingest",
        files={"video": ("clip.mp4", tiny_video_bytes, "video/mp4")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["speaker_order"] == ["SPEAKER_00", "SPEAKER_01"]
    assert len(body["chunks"]) == len(sample_whisper_segments)
    assert body["meta"]["total_speakers"] == 2


def test_ingest_returns_502_on_upstream_failure(client, tiny_video_bytes, monkeypatch):
    async def failing_call_whisper(audio_bytes, filename="audio.wav"):
        raise httpx.ConnectError("whisper unreachable")

    monkeypatch.setattr(clients, "call_whisper", failing_call_whisper)

    response = client.post(
        "/ingest",
        files={"video": ("clip.mp4", tiny_video_bytes, "video/mp4")},
    )

    assert response.status_code == 502
