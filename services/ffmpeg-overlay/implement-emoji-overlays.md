# Agent Task: Add Emoji Overlays to ffmpeg-overlay Service

## Context

This service accepts a video file and a sentiment timeline, builds an FFmpeg filter chain, and returns a rendered MP4. The current implementation uses only `drawbox` filters passed via `-vf`. This task adds per-chunk emoji overlays (one PNG per timeline entry) using FFmpeg's `overlay` filter and `-filter_complex`.

**Phase 1 (asset sourcing) has already been done.** The directory `services/ffmpeg-overlay/assets/emoji/` contains 7 PNG files sourced from [Twemoji](https://github.com/twitter/twemoji) (Apache 2.0):

```
assets/emoji/
    very_negative.png       # 😡  Twemoji U+1F621
    negative.png            # 😞  Twemoji U+1F61E
    slightly_negative.png   # 😕  Twemoji U+1F615
    neutral.png             # 😐  Twemoji U+1F610
    slightly_positive.png   # 🙂  Twemoji U+1F642
    positive.png            # 😊  Twemoji U+1F60A
    very_positive.png       # 😄  Twemoji U+1F604
```

Each PNG is 72 x 72 px with a transparent background.

**Twemoji attribution** must appear in `README.md` (both root and service). The exact wording to add is:

> Emoji graphics provided by [Twemoji](https://github.com/twitter/twemoji), Copyright 2019 Twitter, Inc and other contributors. Licensed under [Apache 2.0](https://creativecommons.org/licenses/by/4.0/).

---

## Existing code to understand before editing

Read these files carefully before making any changes:

- `services/ffmpeg-overlay/filter_generator.py` — `TimelineEntry` Pydantic model, `build_filter_chain()`, `hex_to_ffmpeg_color()`
- `services/ffmpeg-overlay/main.py` — `/preview` and `/render` FastAPI endpoints; note how the FFmpeg subprocess is constructed
- `services/ffmpeg-overlay/tests/test_filter_generator.py` — existing test structure and helper `_entry()` pattern
- `services/ffmpeg-overlay/tests/test_preview.py` — existing assertions on the `/preview` response shape
- `services/ffmpeg-overlay/tests/conftest.py` — shared fixtures (`client`, `sample_timeline`, `tiny_video_bytes`)

---

## Phase 2 — `filter_generator.py` changes

### 2a. Score-to-tone mapping

Add these two items at module level, **before** the `TimelineEntry` class:

```python
from pathlib import Path

EMOJI_ASSET_DIR = Path(__file__).parent / "assets" / "emoji"

# Inclusive score ranges → tone file stem (matches filenames in EMOJI_ASSET_DIR)
_SCORE_RANGES: list[tuple[int, int, str]] = [
    (0,  1,  "very_negative"),
    (2,  2,  "negative"),
    (3,  4,  "slightly_negative"),
    (5,  5,  "neutral"),
    (6,  7,  "slightly_positive"),
    (8,  9,  "positive"),
    (10, 10, "very_positive"),
]


def score_to_tone(score: int) -> str:
    """Return the tone name (emoji file stem) for a sentiment score 0–10."""
    for lo, hi, tone in _SCORE_RANGES:
        if lo <= score <= hi:
            return tone
    raise ValueError(f"score must be 0–10, got {score}")
```

### 2b. New `build_filter_graph()` function

Add this function **after** `build_filter_chain()`. Do not modify `build_filter_chain()`.

```python
def build_filter_graph(
    entries: List[TimelineEntry],
    emoji_dir: Path = EMOJI_ASSET_DIR,
    emoji_x: int = 68,
    emoji_y: int = 68,
) -> tuple[list[Path], str]:
    """
    Build a full FFmpeg -filter_complex graph that combines drawbox color bands
    with per-chunk emoji overlays.

    Returns
    -------
    emoji_paths : list[Path]
        One Path per timeline entry (may repeat tones). The caller must pass
        each path as a separate ``-i`` argument to FFmpeg, in order starting
        at input index 1. The last path corresponds to input ``[N:v]`` where
        N == len(entries).

    filter_complex : str
        A semicolon-separated filter_complex string ready for ``ffmpeg -filter_complex``.
        The final output stream is labeled ``[out]`` — the caller must pass
        ``-map [out]`` to FFmpeg.

    Raises
    ------
    FileNotFoundError
        If any required emoji PNG is not found in *emoji_dir*. This is a
        deployment error and should fail loudly.
    ValueError
        If *entries* is empty.
    """
    if not entries:
        raise ValueError("entries must not be empty")

    emoji_paths: list[Path] = []
    for entry in entries:
        tone = score_to_tone(entry.score)
        png = emoji_dir / f"{tone}.png"
        if not png.exists():
            raise FileNotFoundError(
                f"Emoji asset missing: {png}. "
                "Ensure assets/emoji/ is present in the deployment image."
            )
        emoji_paths.append(png)

    # Part 1: apply all drawboxes to [0:v] → [boxed]
    drawbox_chain = build_filter_chain(entries)
    parts = [f"[0:v]{drawbox_chain}[boxed]"]

    # Part 2: chain overlay filters, one per entry
    # Input indices: video=0, emoji[0]=1, emoji[1]=2, …
    prev_label = "boxed"
    for i, entry in enumerate(entries):
        out_label = "out" if i == len(entries) - 1 else f"s{i}"
        parts.append(
            f"[{prev_label}][{i + 1}:v]"
            f"overlay={emoji_x}:{emoji_y}:"
            f"enable='between(t,{entry.start},{entry.end})'"
            f"[{out_label}]"
        )
        prev_label = out_label

    return emoji_paths, ";".join(parts)
```

**Example output** for a two-entry timeline:

```
# emoji_paths = [Path("assets/emoji/slightly_positive.png"), Path("assets/emoji/positive.png")]

# filter_complex:
[0:v]drawbox=x=0:y=0:w=200:h=200:color=0x90EE90@0.70:t=fill:enable='between(t,0.0,3.2)',drawbox=x=0:y=0:w=200:h=200:color=0x32CD32@0.70:t=fill:enable='between(t,3.2,7.5)'[boxed];[boxed][1:v]overlay=68:68:enable='between(t,0.0,3.2)'[s0];[s0][2:v]overlay=68:68:enable='between(t,3.2,7.5)'[out]
```

---

## Phase 3 — `main.py` changes

### 3a. Import addition

Add `Path` to the imports at the top of `main.py`:

```python
from pathlib import Path
```

Update the `filter_generator` import line to also import the new function:

```python
from filter_generator import TimelineEntry, build_filter_chain, build_filter_graph
```

### 3b. Update `/render` endpoint

Replace the block that currently builds and runs the FFmpeg command. The new version:

1. Calls `build_filter_graph(entries)` to get `(emoji_paths, filter_complex)`
2. Copies each emoji PNG into the tmpdir as `emoji_0.png`, `emoji_1.png`, … (so the subprocess gets stable local paths; the source paths may contain special characters)
3. Builds the FFmpeg command with multiple `-i` arguments followed by `-filter_complex` and `-map [out]`
4. Removes the old `-vf filter_chain` flag entirely

Replace the FFmpeg command construction block (currently `cmd = ["ffmpeg", "-y", ...]`) with:

```python
    emoji_paths, filter_complex = build_filter_graph(entries)

    # Copy emoji PNGs into tmpdir so subprocess paths are simple and safe
    local_emoji: list[str] = []
    for idx, src in enumerate(emoji_paths):
        dst = os.path.join(tmpdir, f"emoji_{idx}.png")
        import shutil as _shutil
        _shutil.copy2(src, dst)
        local_emoji.append(dst)

    # Build FFmpeg command with multiple inputs and filter_complex
    cmd = ["ffmpeg", "-y", "-i", input_path]
    for ep in local_emoji:
        cmd += ["-i", ep]
    cmd += [
        "-filter_complex", filter_complex,
        "-map", "[out]",
        "-c:a", "copy",
        output_path,
    ]
```

> **Note:** `shutil` is already imported at the top of `main.py`. Remove the `import shutil as _shutil` inline import and use the existing `shutil.copy2(src, dst)` directly.

### 3c. Update `/preview` endpoint

The preview response currently returns `{"filter_chain": "..."}`. Extend it to also return the `filter_complex` string. Because `/preview` doesn't write files it cannot validate that emoji PNGs exist — catch `FileNotFoundError` and omit the key in that case:

```python
@app.post("/preview")
async def preview(timeline: List[TimelineEntry]):
    """Return filter strings for a given timeline without rendering."""
    if not timeline:
        raise HTTPException(status_code=422, detail="timeline must not be empty")

    result: dict = {"filter_chain": build_filter_chain(timeline)}
    try:
        _, filter_complex = build_filter_graph(timeline)
        result["filter_complex"] = filter_complex
    except FileNotFoundError:
        # Assets not present in this environment (e.g. bare dev checkout
        # without the emoji directory); degrade gracefully for preview only.
        pass
    return result
```

---

## Phase 4 — Dockerfile

**No changes required.** The existing `COPY . .` instruction already copies `assets/emoji/` into the image.

---

## Phase 5 — Tests

### 5a. `tests/test_filter_generator.py` additions

Append two new test classes at the **end** of the file. Do not modify any existing tests.

```python
class TestScoreToTone:
    """score_to_tone maps score integers to tone name strings."""

    @pytest.mark.parametrize("score,expected", [
        (0,  "very_negative"),
        (1,  "very_negative"),
        (2,  "negative"),
        (3,  "slightly_negative"),
        (4,  "slightly_negative"),
        (5,  "neutral"),
        (6,  "slightly_positive"),
        (7,  "slightly_positive"),
        (8,  "positive"),
        (9,  "positive"),
        (10, "very_positive"),
    ])
    def test_score_maps_to_expected_tone(self, score, expected):
        from filter_generator import score_to_tone
        assert score_to_tone(score) == expected

    def test_out_of_range_raises(self):
        from filter_generator import score_to_tone
        with pytest.raises(ValueError):
            score_to_tone(11)


class TestBuildFilterGraph:
    """build_filter_graph returns correct (emoji_paths, filter_complex) pairs."""

    def _make_emoji_dir(self, tmp_path: Path, tones: list[str]) -> Path:
        """Create a fake emoji directory with zero-byte PNG stubs."""
        d = tmp_path / "emoji"
        d.mkdir()
        for tone in tones:
            (d / f"{tone}.png").write_bytes(b"")
        return d

    ALL_TONES = [
        "very_negative", "negative", "slightly_negative", "neutral",
        "slightly_positive", "positive", "very_positive",
    ]

    def _entry(self, start=0.0, end=3.0, score=5, color="#CCCCCC"):
        return TimelineEntry(start=start, end=end, score=score, color=color)

    def test_returns_one_emoji_path_per_entry(self, tmp_path):
        from filter_generator import build_filter_graph
        emoji_dir = self._make_emoji_dir(tmp_path, self.ALL_TONES)
        entries = [self._entry(0.0, 3.0, 6), self._entry(3.0, 6.0, 8)]
        paths, _ = build_filter_graph(entries, emoji_dir=emoji_dir)
        assert len(paths) == 2

    def test_emoji_path_matches_tone(self, tmp_path):
        from filter_generator import build_filter_graph
        emoji_dir = self._make_emoji_dir(tmp_path, self.ALL_TONES)
        entries = [self._entry(score=0)]  # very_negative
        paths, _ = build_filter_graph(entries, emoji_dir=emoji_dir)
        assert paths[0].name == "very_negative.png"

    def test_filter_complex_contains_boxed_label(self, tmp_path):
        from filter_generator import build_filter_graph
        emoji_dir = self._make_emoji_dir(tmp_path, self.ALL_TONES)
        _, fc = build_filter_graph([self._entry()], emoji_dir=emoji_dir)
        assert "[boxed]" in fc

    def test_filter_complex_final_output_labeled_out(self, tmp_path):
        from filter_generator import build_filter_graph
        emoji_dir = self._make_emoji_dir(tmp_path, self.ALL_TONES)
        _, fc = build_filter_graph([self._entry()], emoji_dir=emoji_dir)
        assert "[out]" in fc

    def test_filter_complex_single_entry_no_intermediate_labels(self, tmp_path):
        from filter_generator import build_filter_graph
        emoji_dir = self._make_emoji_dir(tmp_path, self.ALL_TONES)
        _, fc = build_filter_graph([self._entry()], emoji_dir=emoji_dir)
        # With one entry there should be no [s0], [s1] etc — only [boxed] and [out]
        assert "[s0]" not in fc

    def test_filter_complex_multi_entry_intermediate_labels(self, tmp_path):
        from filter_generator import build_filter_graph
        emoji_dir = self._make_emoji_dir(tmp_path, self.ALL_TONES)
        entries = [
            self._entry(0.0, 3.0, 6),
            self._entry(3.0, 6.0, 8),
            self._entry(6.0, 9.0, 2),
        ]
        _, fc = build_filter_graph(entries, emoji_dir=emoji_dir)
        assert "[s0]" in fc
        assert "[s1]" in fc
        assert "[s2]" not in fc  # last entry uses [out], not [s2]

    def test_filter_complex_overlay_count_matches_entries(self, tmp_path):
        from filter_generator import build_filter_graph
        emoji_dir = self._make_emoji_dir(tmp_path, self.ALL_TONES)
        entries = [self._entry(float(i), float(i + 1), 5) for i in range(4)]
        _, fc = build_filter_graph(entries, emoji_dir=emoji_dir)
        assert fc.count("overlay=") == 4

    def test_filter_complex_contains_timestamps(self, tmp_path):
        from filter_generator import build_filter_graph
        emoji_dir = self._make_emoji_dir(tmp_path, self.ALL_TONES)
        entry = TimelineEntry(start=12.4, end=15.8, score=5, color="#CCCCCC")
        _, fc = build_filter_graph([entry], emoji_dir=emoji_dir)
        assert "between(t,12.4,15.8)" in fc

    def test_missing_emoji_png_raises_file_not_found(self, tmp_path):
        from filter_generator import build_filter_graph
        emoji_dir = self._make_emoji_dir(tmp_path, ["neutral"])  # only neutral present
        entry = self._entry(score=0)  # needs very_negative.png
        with pytest.raises(FileNotFoundError, match="very_negative.png"):
            build_filter_graph([entry], emoji_dir=emoji_dir)

    def test_empty_entries_raises_value_error(self, tmp_path):
        from filter_generator import build_filter_graph
        emoji_dir = self._make_emoji_dir(tmp_path, self.ALL_TONES)
        with pytest.raises(ValueError, match="empty"):
            build_filter_graph([], emoji_dir=emoji_dir)

    def test_custom_emoji_position(self, tmp_path):
        from filter_generator import build_filter_graph
        emoji_dir = self._make_emoji_dir(tmp_path, self.ALL_TONES)
        _, fc = build_filter_graph([self._entry()], emoji_dir=emoji_dir, emoji_x=10, emoji_y=20)
        assert "overlay=10:20:" in fc
```

Add `from pathlib import Path` to the imports at the top of `test_filter_generator.py`.

### 5b. `tests/test_preview.py` additions

Append these tests to the existing `TestPreviewEndpoint` class:

```python
    def test_preview_includes_filter_chain_key(self, client, sample_timeline):
        response = client.post("/preview", json=sample_timeline)
        assert "filter_chain" in response.json()

    def test_preview_filter_complex_contains_overlay_when_assets_present(self, client, sample_timeline):
        """filter_complex key is present only when emoji assets exist on disk."""
        import os
        from pathlib import Path
        import filter_generator as fg
        emoji_dir = fg.EMOJI_ASSET_DIR
        if not emoji_dir.exists():
            pytest.skip("Emoji assets not present — skipping filter_complex assertion")
        response = client.post("/preview", json=sample_timeline)
        assert "filter_complex" in response.json()
        assert "overlay=" in response.json()["filter_complex"]

    def test_preview_filter_complex_absent_without_assets(self, client, monkeypatch, tmp_path):
        """filter_complex key is omitted gracefully when assets directory is empty."""
        import filter_generator as fg
        monkeypatch.setattr(fg, "EMOJI_ASSET_DIR", tmp_path / "nonexistent")
        response = client.post("/preview", json=[
            {"start": 0.0, "end": 3.0, "score": 5, "color": "#CCCCCC"}
        ])
        assert response.status_code == 200
        assert "filter_chain" in response.json()
        assert "filter_complex" not in response.json()
```

### 5c. `tests/test_render.py` — no changes required

The existing render tests should pass unchanged once the emoji assets are present. FFmpeg will compose each PNG into the output during its time window. No new test class is needed unless you want t        import filter_generator as fgo explicitly assert emoji presence (which would require frame inspection tools outside scope).

---

## Phase 6 — Documentation

### 6a. `services/ffmpeg-overlay/README.md`

1. Add an **Emoji** column to the **Timeline entry fields** table:

| Field | Type | Constraints | Description |
|---|---|---|---|
| `start` | float | ≥ 0 | Chunk start time in seconds |
| `end` | float | > `start` | Chunk end time in seconds |
| `score` | int | 0–10 | Sentiment score; also determines emoji overlay |
| `color` | string | `#RRGGBB` | Hex color for the overlay box |

2. Add a new **Emoji overlays** section after **How the overlay works**:

```markdown
## Emoji overlays

Each chunk score is mapped to one of seven emoji PNGs (64×64, transparent background) and composited over the color box at position x=68, y=68 (centred within the 200×200 box) during that chunk's time window.

| Tone | Score range | Emoji |
|---|---|---|
| VERY_NEGATIVE | 0–1 | 😡 |
| NEGATIVE | 2 | 😞 |
| SLIGHTLY_NEGATIVE | 3–4 | 😕 |
| NEUTRAL | 5 | 😐 |
| SLIGHTLY_POSITIVE | 6–7 | 🙂 |
| POSITIVE | 8–9 | 😊 |
| VERY_POSITIVE | 10 | 😄 |

The assets live in `assets/emoji/` and are bundled in the Docker image via `COPY . .`.

Emoji graphics provided by [Twemoji](https://github.com/twitter/twemoji), Copyright 2019 Twitter, Inc and other contributors. Licensed under [Apache 2.0](https://www.apache.org/licenses/LICENSE-2.0).
```

3. Update the **`/preview` Response** example to show the new `filter_complex` key alongside `filter_chain`.

### 6b. Root `README.md`

Add an **Emoji** column to the **Sentiment tone map** table:

| Tone | Score | Color | Emoji |
|---|---|---|---|
| VERY_NEGATIVE | 0 | `#FF0000` | 😡 |
| NEGATIVE | 2 | `#FF4500` | 😞 |
| SLIGHTLY_NEGATIVE | 3 | `#FFA500` | 😕 |
| NEUTRAL | 5 | `#CCCCCC` | 😐 |
| SLIGHTLY_POSITIVE | 6 | `#90EE90` | 🙂 |
| POSITIVE | 8 | `#32CD32` | 😊 |
| VERY_POSITIVE | 10 | `#008000` | 😄 |

Add the Twemoji attribution line below the table:

> Emoji graphics provided by [Twemoji](https://github.com/twitter/twemoji), Copyright 2019 Twitter, Inc and other contributors. Licensed under [Apache 2.0](https://www.apache.org/licenses/LICENSE-2.0).

---

## Verification checklist

After implementation, run each step in order:

```bash
cd services/ffmpeg-overlay
conda activate video-overlay

# 1. Syntax check
make lint

# 2. Unit + API tests (no FFmpeg, no real emoji PNGs needed for most cases)
make test-unit

# 3. Full test suite including render (requires FFmpeg + real emoji PNGs in assets/emoji/)
make test
```

**Manual spot-check (requires running service + real emoji assets):**

```bash
# Start the service
uvicorn main:app --reload --port 8001

# Preview — response must include both keys
curl -s -X POST http://localhost:8001/preview \
  -H "Content-Type: application/json" \
  -d '[{"start":0,"end":3.2,"score":6,"color":"#90EE90"}]' | python3 -m json.tool
# Expected: {"filter_chain": "drawbox=...", "filter_complex": "[0:v]drawbox=...[boxed];[boxed][1:v]overlay=68:68:enable='between(t,0,3.2)'[out]"}

# Render — output MP4 must have 😊 visible in the top-left corner
curl -X POST http://localhost:8001/render \
  -F "video=@/path/to/test.mp4" \
  -F 'timeline=[{"start":0,"end":3.2,"score":6,"color":"#90EE90"}]' \
  -o rendered.mp4
```

---

## Constraints and gotchas

- **Do not modify `build_filter_chain()`**. Existing tests depend on its exact output format and it is reused inside `build_filter_graph()`.
- **`TimelineEntry` model is unchanged.** Emoji are derived from `score` only — no new fields added.
- **Fail loudly on missing assets.** The `FileNotFoundError` in `build_filter_graph()` is intentional — if an emoji PNG is absent in production it is a deployment error, not a graceful degradation scenario.
- **`shutil` is already imported** in `main.py` as `import shutil`. Do not add a second import.
- **The `-map [out]` flag is required** when using `-filter_complex` with a named output label. Without it FFmpeg picks the first stream automatically, which may not be `[out]`.
- **Emoji PNG dimensions**: the assets are 64×64 px. The default position `emoji_x=68, emoji_y=68` centres the icon inside the existing 200×200 `drawbox` region. If the emoji asset size changes, adjust accordingly: `x = (box_w - emoji_w) // 2`.
