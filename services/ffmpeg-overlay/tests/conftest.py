"""
Shared pytest fixtures for the ffmpeg-overlay service.

Tiny video generation
─────────────────────
Rather than committing a binary test fixture to git, the ``tiny_video_path``
fixture generates a 1-second 320x240 black MP4 at test-session scope using
FFmpeg itself. Tests that depend on this fixture are automatically skipped
when FFmpeg is not available in the test environment.

E2E note
────────
The end-to-end suite (tests/e2e/ at the repo root) will test the full pipeline
by calling live services over HTTP. Those tests are out of scope until MVP
is complete and all three services are stable.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Ensure the service root is on the path so imports resolve correctly when
# running pytest from anywhere inside the repo.
sys.path.insert(0, str(Path(__file__).parent.parent))

from main import app  # noqa: E402

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def sample_timeline() -> list:
    return json.loads((FIXTURES_DIR / "sample_timeline.json").read_text())


@pytest.fixture(scope="session")
def tiny_video_path(tmp_path_factory):
    """
    Generate a 1-second 320x240 black H.264 MP4 for integration tests.

    Uses FFmpeg's lavfi ``color`` source — no input file required.
    The generated file lives in pytest's session-scoped tmp directory and
    is never committed to the repository.

    Skips all dependent tests if FFmpeg is not installed.
    """
    out = tmp_path_factory.mktemp("video") / "tiny.mp4"
    result = subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", "color=c=black:s=320x240:d=1:r=10",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            str(out),
        ],
        capture_output=True,
    )
    if result.returncode != 0:
        pytest.skip("FFmpeg not available — skipping render integration tests")
    return out


@pytest.fixture(scope="session")
def tiny_video_bytes(tiny_video_path) -> bytes:
    return tiny_video_path.read_bytes()
