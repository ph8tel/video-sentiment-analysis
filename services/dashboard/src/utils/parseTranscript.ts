export interface TranscriptChunk {
  start: number;
  end: number;
  text: string;
}

const secondsLabelRe = /^\d+(?:\.\d+)?\s+seconds?$/i;

function parseTimestamp(raw: string): number {
  const value = raw.trim();

  if (/^\d+(?:\.\d+)?$/.test(value)) {
    return Number(value);
  }

  const parts = value.split(":");
  if (parts.length < 2 || parts.length > 3) {
    throw new Error(`Unsupported timestamp format: ${raw}`);
  }

  const nums = parts.map((part) => Number(part));
  if (nums.some((num) => Number.isNaN(num) || num < 0)) {
    throw new Error(`Unsupported timestamp format: ${raw}`);
  }

  if (parts.length === 2) {
    const [minutes, seconds] = nums;
    return minutes * 60 + seconds;
  }

  const [hours, minutes, seconds] = nums;
  return hours * 3600 + minutes * 60 + seconds;
}

function asTranscriptChunks(data: unknown): TranscriptChunk[] | null {
  if (!Array.isArray(data)) {
    return null;
  }

  const chunks: TranscriptChunk[] = [];
  for (const item of data) {
    if (
      !item ||
      typeof item !== "object" ||
      !("start" in item) ||
      !("end" in item) ||
      !("text" in item)
    ) {
      return null;
    }

    const start = Number((item as { start: unknown }).start);
    const end = Number((item as { end: unknown }).end);
    const text = String((item as { text: unknown }).text ?? "").trim();

    if (!Number.isFinite(start) || !Number.isFinite(end) || end <= start || !text) {
      return null;
    }

    chunks.push({ start, end, text });
  }

  return chunks.length ? chunks : null;
}

function parseRawBlocks(raw: string): TranscriptChunk[] {
  const lines = raw.split(/\r?\n/).map((line) => line.trim());
  const starts: number[] = [];
  const texts: string[] = [];

  let idx = 0;
  while (idx < lines.length) {
    while (idx < lines.length && !lines[idx]) {
      idx += 1;
    }

    if (idx >= lines.length) {
      break;
    }

    const start = parseTimestamp(lines[idx]);
    starts.push(start);
    idx += 1;

    if (idx < lines.length && secondsLabelRe.test(lines[idx])) {
      idx += 1;
    }

    const textLines: string[] = [];
    while (idx < lines.length) {
      const candidate = lines[idx];
      if (!candidate) {
        idx += 1;
        continue;
      }

      try {
        parseTimestamp(candidate);
        break;
      } catch {
        textLines.push(candidate);
        idx += 1;
      }
    }

    const text = textLines.join(" ").trim();
    if (!text) {
      throw new Error("Missing transcript text for one or more chunks.");
    }
    texts.push(text);
  }

  if (!starts.length || starts.length !== texts.length) {
    throw new Error("Could not parse transcript blocks.");
  }

  const deltas: number[] = [];
  for (let i = 1; i < starts.length; i += 1) {
    const delta = starts[i] - starts[i - 1];
    if (delta <= 0) {
      throw new Error("Transcript timestamps must be strictly increasing.");
    }
    deltas.push(delta);
  }

  const fallbackDuration = deltas.length
    ? deltas.sort((a, b) => a - b)[Math.floor(deltas.length / 2)]
    : 3;

  const chunks: TranscriptChunk[] = [];
  for (let i = 0; i < starts.length; i += 1) {
    const start = starts[i];
    const end = i < starts.length - 1 ? starts[i + 1] : start + fallbackDuration;
    chunks.push({ start, end, text: texts[i] });
  }

  return chunks;
}

export function parseTranscript(raw: string): TranscriptChunk[] {
  const trimmed = raw.trim();
  if (!trimmed) {
    throw new Error("Transcript file is empty.");
  }

  try {
    const parsed = JSON.parse(trimmed) as unknown;
    const chunks = asTranscriptChunks(parsed);
    if (chunks) {
      return chunks;
    }
  } catch {
    // Not JSON input; fall through to raw block parser.
  }

  return parseRawBlocks(trimmed);
}