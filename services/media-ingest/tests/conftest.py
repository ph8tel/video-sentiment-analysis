import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

from main import app  # noqa: E402

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def sample_whisper_segments() -> list:
    return json.loads((FIXTURES_DIR / "sample_whisper_segments.json").read_text())


@pytest.fixture(scope="session")
def sample_diarization() -> dict:
    return json.loads((FIXTURES_DIR / "sample_diarization.json").read_text())
