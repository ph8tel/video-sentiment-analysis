#!/usr/bin/env python3

import argparse
import json
import re
from pathlib import Path
from statistics import median


TIMESTAMP_RE = re.compile(r"^(?:(\d+):)?(\d{1,2}):(\d{2})(?:\.(\d+))?$|^(\d+)(?:\.(\d+))?$")
SECONDS_LABEL_RE = re.compile(r"^\d+(?:\.\d+)?\s+seconds?$", re.IGNORECASE)


def parse_timestamp(raw: str) -> float:
    value = raw.strip()
    match = TIMESTAMP_RE.fullmatch(value)
    if not match:
        raise ValueError(f"Unsupported timestamp format: {raw!r}")

    if match.group(5) is not None:
        whole_seconds = int(match.group(5))
        fractional = match.group(6) or "0"
        return whole_seconds + float(f"0.{fractional}")

    hours = int(match.group(1) or 0)
    minutes = int(match.group(2))
    seconds = int(match.group(3))
    fractional = match.group(4) or "0"
    return hours * 3600 + minutes * 60 + seconds + float(f"0.{fractional}")


def is_timestamp_line(raw: str) -> bool:
    try:
        parse_timestamp(raw)
    except ValueError:
        return False
    return True


def estimate_last_duration(starts: list[float], fallback: float) -> float:
    if len(starts) < 2:
        return fallback

    durations = [later - earlier for earlier, later in zip(starts, starts[1:])]
    positive_durations = [duration for duration in durations if duration > 0]
    if not positive_durations:
        return fallback
    return median(positive_durations)


def parse_blocks(raw_text: str) -> list[dict[str, float | str]]:
    lines = [line.strip() for line in raw_text.splitlines()]
    blocks: list[dict[str, float | str]] = []
    index = 0

    while index < len(lines):
        line = lines[index]
        if not line:
            index += 1
            continue

        if not is_timestamp_line(line):
            raise ValueError(
                f"Expected a timestamp at line {index + 1}, found {line!r}"
            )

        start = parse_timestamp(line)
        index += 1

        if index < len(lines) and SECONDS_LABEL_RE.fullmatch(lines[index]):
            index += 1

        text_lines: list[str] = []
        while index < len(lines):
            candidate = lines[index]
            if not candidate:
                index += 1
                continue
            if is_timestamp_line(candidate):
                break
            text_lines.append(candidate)
            index += 1

        text = " ".join(text_lines).strip()
        if not text:
            raise ValueError(f"Missing transcript text for chunk starting at {line!r}")

        blocks.append({"start": start, "text": text})

    if not blocks:
        raise ValueError("No transcript chunks found")

    return blocks


def to_transcript_json(
    raw_text: str,
    last_end: float | None,
    default_last_duration: float,
) -> list[dict[str, float | str]]:
    blocks = parse_blocks(raw_text)
    starts = [float(block["start"]) for block in blocks]

    if last_end is None:
        last_end = starts[-1] + estimate_last_duration(starts, default_last_duration)

    if last_end <= starts[-1]:
        raise ValueError("Final end time must be greater than the last start time")

    transcript: list[dict[str, float | str]] = []
    for current, following in zip(blocks, starts[1:]):
        start = float(current["start"])
        end = float(following)
        if end <= start:
            raise ValueError("Timestamps must be strictly increasing")
        transcript.append({"start": start, "end": end, "text": str(current["text"])})

    last_block = blocks[-1]
    transcript.append(
        {
            "start": float(last_block["start"]),
            "end": float(last_end),
            "text": str(last_block["text"]),
        }
    )
    return transcript


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Convert timestamp blocks like '0:03 / 3 seconds / text' into the "
            "transcript JSON format used by this repo."
        )
    )
    parser.add_argument("input", type=Path, help="Path to the raw transcript text file")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Where to write the JSON output. Defaults to stdout.",
    )
    parser.add_argument(
        "--last-end",
        type=float,
        default=None,
        help="Explicit end time for the final chunk in seconds.",
    )
    parser.add_argument(
        "--default-last-duration",
        type=float,
        default=3.0,
        help=(
            "Fallback duration for the final chunk when there is no next timestamp. "
            "If omitted, the script uses the median prior chunk length, or this value "
            "when only one chunk exists."
        ),
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    raw_text = args.input.read_text(encoding="utf-8")
    transcript = to_transcript_json(
        raw_text,
        last_end=args.last_end,
        default_last_duration=args.default_last_duration,
    )

    output = json.dumps(transcript, indent=2)
    if args.output:
        args.output.write_text(f"{output}\n", encoding="utf-8")
    else:
        print(output)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())