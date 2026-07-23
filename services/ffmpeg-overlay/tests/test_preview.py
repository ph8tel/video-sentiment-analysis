"""
Integration tests for the /health and /preview endpoints.

No FFmpeg or video files are required — these tests exercise the filter
chain generation and API validation logic only.
"""


class TestHealthEndpoint:
    def test_returns_200(self, client):
        response = client.get("/health")
        assert response.status_code == 200

    def test_returns_ok_status(self, client):
        response = client.get("/health")
        assert response.json()["status"] == "ok"


class TestPreviewEndpoint:
    def test_valid_timeline_returns_filter_chain(self, client, sample_timeline):
        response = client.post("/preview", json=sample_timeline)
        assert response.status_code == 200
        assert "filter_chain" in response.json()

    def test_filter_chain_contains_drawbox(self, client, sample_timeline):
        response = client.post("/preview", json=sample_timeline)
        assert "drawbox=" in response.json()["filter_chain"]

    def test_filter_chain_has_one_segment_per_chunk(self, client, sample_timeline):
        response = client.post("/preview", json=sample_timeline)
        chain = response.json()["filter_chain"]
        assert chain.count("drawbox=") == len(sample_timeline)

    def test_filter_chain_contains_correct_timestamps(self, client):
        response = client.post("/preview", json=[
            {"start": 12.4, "end": 15.8, "score": 2, "color": "#FF4500"}
        ])
        assert response.status_code == 200
        assert "between(t,12.4,15.8)" in response.json()["filter_chain"]

    def test_filter_chain_contains_ffmpeg_color_format(self, client):
        response = client.post("/preview", json=[
            {"start": 0.0, "end": 3.0, "score": 2, "color": "#FF4500"}
        ])
        chain = response.json()["filter_chain"]
        # FFmpeg uses 0x prefix, not #
        assert "0xFF4500" in chain
        assert "#FF4500" not in chain

    def test_empty_timeline_returns_422(self, client):
        response = client.post("/preview", json=[])
        assert response.status_code == 422

    def test_invalid_color_returns_422(self, client):
        response = client.post("/preview", json=[
            {"start": 0.0, "end": 5.0, "score": 6, "color": "not-a-color"}
        ])
        assert response.status_code == 422

    def test_end_before_start_returns_422(self, client):
        response = client.post("/preview", json=[
            {"start": 10.0, "end": 5.0, "score": 6, "color": "#90EE90"}
        ])
        assert response.status_code == 422

    def test_score_out_of_range_returns_422(self, client):
        response = client.post("/preview", json=[
            {"start": 0.0, "end": 5.0, "score": 99, "color": "#90EE90"}
        ])
        assert response.status_code == 422

    def test_missing_required_field_returns_422(self, client):
        response = client.post("/preview", json=[
            {"start": 0.0, "end": 5.0, "score": 6}  # missing color
        ])
        assert response.status_code == 422
