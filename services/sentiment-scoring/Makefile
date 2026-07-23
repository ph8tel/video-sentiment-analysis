# Dev environment: use the shared `video-overlay` conda env (Python 3.11).
#
# First-time setup (from repo root):
#   conda create -n video-overlay python=3.11 -y
#   conda activate video-overlay
#   pip install -r requirements-dev.txt

PYTHON := python
PYTEST := pytest

.PHONY: test test-unit test-api lint

test:
	$(PYTEST) -v

test-unit:
	$(PYTEST) tests/test_color_mapper.py tests/test_llm_client.py tests/test_scorer.py -v

test-api:
	$(PYTEST) tests/test_api.py -v

lint:
	$(PYTHON) -m py_compile color_mapper.py llm_client.py scorer.py main.py
