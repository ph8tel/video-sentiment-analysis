"""
Integration tests for the /render-multi endpoint.

Tests that require a real video (``tiny_video_bytes``) are automatically
skipped when FFmpeg is not available in the test environment — see conftest.py.
"""

import json


def _timeline_json(sample_timeline, n):
    return json.dumps(sample_timeline[:n])


class TestRenderMultiEndpoint:
    def test_valid_request_returns_200(self, client, tiny_video_bytes, sample_timeline):
        response = client.post(
            "/render-multi",
            files={"video": ("test.mp4", tiny_video_bytes, "video/mp4")},
            data={
                "overall_timeline": _timeline_json(sample_timeline, 3),
                "speaker_left_timeline": _timeline_json(sample_timeline, 1),
                "speaker_right_timeline": _timeline_json(sample_timeline, 2),
            },
        )
        assert response.status_code == 200

    def test_valid_request_returns_mp4_content_type(self, client, tiny_video_bytes, sample_timeline):
        response = client.post(
            "/render-multi",
            files={"video": ("test.mp4", tiny_video_bytes, "video/mp4")},
            data={
                "overall_timeline": _timeline_json(sample_timeline, 3),
                "speaker_left_timeline": _timeline_json(sample_timeline, 1),
                "speaker_right_timeline": _timeline_json(sample_timeline, 2),
            },
        )
        assert "video/mp4" in response.headers["content-type"]

    def test_one_empty_timeline_is_allowed(self, client, tiny_video_bytes, sample_timeline):
        response = client.post(
            "/render-multi",
            files={"video": ("test.mp4", tiny_video_bytes, "video/mp4")},
            data={
                "overall_timeline": _timeline_json(sample_timeline, 3),
                "speaker_left_timeline": "[]",
                "speaker_right_timeline": "[]",
            },
        )
        assert response.status_code == 200

    def test_all_empty_timelines_returns_422(self, client, tiny_video_bytes):
        response = client.post(
            "/render-multi",
            files={"video": ("test.mp4", tiny_video_bytes, "video/mp4")},
            data={
                "overall_timeline": "[]",
                "speaker_left_timeline": "[]",
                "speaker_right_timeline": "[]",
            },
        )
        assert response.status_code == 422

    def test_invalid_timeline_json_returns_422(self, client, tiny_video_bytes):
        response = client.post(
            "/render-multi",
            files={"video": ("test.mp4", tiny_video_bytes, "video/mp4")},
            data={
                "overall_timeline": "not json",
                "speaker_left_timeline": "[]",
                "speaker_right_timeline": "[]",
            },
        )
        assert response.status_code == 422

    def test_oversized_video_returns_413(self, client, sample_timeline, monkeypatch):
        import main as m
        monkeypatch.setattr(m, "MAX_UPLOAD_SIZE_BYTES", 10)
        response = client.post(
            "/render-multi",
            files={"video": ("test.mp4", b"x" * 11, "video/mp4")},
            data={
                "overall_timeline": _timeline_json(sample_timeline, 3),
                "speaker_left_timeline": "[]",
                "speaker_right_timeline": "[]",
            },
        )
        assert response.status_code == 413

    def test_corrupt_video_returns_500(self, client, sample_timeline):
        response = client.post(
            "/render-multi",
            files={"video": ("bad.mp4", b"this is definitely not a video", "video/mp4")},
            data={
                "overall_timeline": _timeline_json(sample_timeline, 3),
                "speaker_left_timeline": "[]",
                "speaker_right_timeline": "[]",
            },
        )
        assert response.status_code == 500
