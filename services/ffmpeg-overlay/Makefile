# Dev environment uses a conda env named `video-overlay` with Python 3.11
# to match the Docker image and avoid conflicts with the system Python.
#
# First-time setup:
#   conda create -n video-overlay python=3.11 -y
#   conda activate video-overlay
#   pip install -r requirements-dev.txt
#
# All targets assume the `video-overlay` conda env is active.

PYTHON := python
PYTEST := pytest

.PHONY: test test-unit test-render lint

test:
	$(PYTEST) -v

test-unit:
	$(PYTEST) tests/test_filter_generator.py tests/test_preview.py -v

test-render:
	$(PYTEST) tests/test_render.py tests/test_render_multi.py -v

lint:
	$(PYTHON) -m py_compile filter_generator.py main.py
