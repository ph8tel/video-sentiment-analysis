# Media Ingest Service

Accepts a single video of two speakers, extracts audio, transcribes it with a
Whisper STT service and diarizes it with a Pyannote speaker-diarization
service (both running on the host LAN), then merges the two into a
speaker-labeled transcript.

Port: **8003**

---

## API

### `GET /health`
Returns `{"status": "ok"}`.

### `POST /ingest`
`multipart/form-data` with a single `video` field (the source video file).

**Response**
```json
{
  "chunks": [
    {"start": 0.0, "end": 2.1, "text": "...", "speaker": "SPEAKER_00"},
    {"start": 2.4, "end": 4.4, "text": "...", "speaker": "SPEAKER_01"}
  ],
  "speaker_order": ["SPEAKER_00", "SPEAKER_01"],
  "meta": {"total_speakers": 2, "speakers_list": ["SPEAKER_00", "SPEAKER_01"]}
}
```

`speaker_order` lists speakers in order of first appearance — consumers use
this to map the first speaker to the "left" position and the second to
"right".

---

## Configuration

| Variable | Default | Description |
|---|---|---|
| `WHISPER_URL` | `http://192.168.1.188:5000` | Whisper STT service base URL |
| `PYANNOTE_URL` | `http://192.168.1.188:3003` | Pyannote diarization service base URL |
| `NUM_SPEAKERS` | `2` | Speaker count passed to Pyannote's `/diarize` |
| `MAX_UPLOAD_SIZE_MB` | `500` | Max video upload size |
| `MEDIA_INGEST_TIMEOUT` | `600` | Timeout (seconds) for upstream Whisper/Pyannote calls |

---

## How merging works

Each Whisper segment is assigned the diarization speaker whose turn overlaps
it the most (by duration). If a segment falls in a silent gap with no
overlapping turn, it's assigned to the nearest turn by midpoint distance. See
[merge.py](merge.py).

---

## Testing

```bash
make test-unit   # merge logic + API tests (mocked Whisper/Pyannote, real FFmpeg)
```
