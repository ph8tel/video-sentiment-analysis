import { SentimentTimeline } from "../types/sentiment";

/**
 * Parse and minimally validate a sentiment timeline JSON string.
 *
 * Kept separate from the FileUpload component so validation logic can be
 * unit-tested without any DOM or FileReader involvement.
 */
export function parseTimeline(raw: string): SentimentTimeline {
  let data: unknown;
  try {
    data = JSON.parse(raw);
  } catch {
    throw new Error("Invalid JSON — could not parse file.");
  }

  if (
    typeof data !== "object" ||
    data === null ||
    !Array.isArray((data as Record<string, unknown>).chunks) ||
    typeof (data as Record<string, unknown>).overall !== "object"
  ) {
    throw new Error(
      "Invalid sentiment timeline: expected { chunks: [...], overall: {...} }"
    );
  }

  return data as SentimentTimeline;
}
