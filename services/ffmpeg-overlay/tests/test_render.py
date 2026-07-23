"""
Integration tests for the /render endpoint.

Tests that require a real video (``tiny_video_bytes``) are automatically
skipped when FFmpeg is not available in the test environment — see conftest.py.

Tests that use only fake/invalid bytes do not depend on FFmpeg and always run.
"""

import json


class TestRenderEndpoint:
    def test_valid_request_returns_200(self, client, tiny_video_bytes, sample_timeline):
        response = client.post(
            "/render",
            files={"video": ("test.mp4", tiny_video_bytes, "video/mp4")},
            data={"timeline": json.dumps(sample_timeline)},
        )
        assert response.status_code == 200

    def test_valid_request_returns_mp4_content_type(self, client, tiny_video_bytes, sample_timeline):
        response = client.post(
            "/render",
            files={"video": ("test.mp4", tiny_video_bytes, "video/mp4")},
            data={"timeline": json.dumps(sample_timeline)},
        )
        assert "video/mp4" in response.headers["content-type"]

    def test_output_is_non_empty(self, client, tiny_video_bytes, sample_timeline):
        response = client.post(
            "/render",
            files={"video": ("test.mp4", tiny_video_bytes, "video/mp4")},
            data={"timeline": json.dumps(sample_timeline)},
        )
        assert len(response.content) > 1024  # rendered MP4 must be non-trivial

    def test_invalid_timeline_json_returns_422(self, client, tiny_video_bytes):
        response = client.post(
            "/render",
            files={"video": ("test.mp4", tiny_video_bytes, "video/mp4")},
            data={"timeline": "this is not json"},
        )
        assert response.status_code == 422

    def test_empty_timeline_returns_422(self, client, tiny_video_bytes):
        response = client.post(
            "/render",
            files={"video": ("test.mp4", tiny_video_bytes, "video/mp4")},
            data={"timeline": "[]"},
        )
        assert response.status_code == 422

    def test_timeline_not_an_array_returns_422(self, client, tiny_video_bytes):
        response = client.post(
            "/render",
            files={"video": ("test.mp4", tiny_video_bytes, "video/mp4")},
            data={"timeline": json.dumps({"start": 0, "end": 1})},
        )
        assert response.status_code == 422

    def test_oversized_video_returns_413(self, client, sample_timeline, monkeypatch):
        import main as m
        monkeypatch.setattr(m, "MAX_UPLOAD_SIZE_BYTES", 10)
        response = client.post(
            "/render",
            files={"video": ("test.mp4", b"x" * 11, "video/mp4")},
            data={"timeline": json.dumps(sample_timeline)},
        )
        assert response.status_code == 413

    def test_corrupt_video_returns_500(self, client, sample_timeline):
        response = client.post(
            "/render",
            files={"video": ("bad.mp4", b"this is definitely not a video", "video/mp4")},
            data={"timeline": json.dumps(sample_timeline)},
        )
        assert response.status_code == 500
