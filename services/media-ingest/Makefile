# Dev environment uses the shared `video-overlay` conda env (Python 3.11)
# to match the Docker image and avoid conflicts with the system Python.
#
# First-time setup:
#   conda create -n video-overlay python=3.11 -y
#   conda activate video-overlay
#   pip install -r requirements-dev.txt

PYTHON := python
PYTEST := pytest

.PHONY: test test-unit lint

test:
	$(PYTEST) -v

test-unit:
	$(PYTEST) tests/test_merge.py tests/test_api.py -v

lint:
	$(PYTHON) -m py_compile main.py merge.py clients.py
