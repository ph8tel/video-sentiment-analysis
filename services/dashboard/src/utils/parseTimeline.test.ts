import { describe, it, expect } from "vitest";
import { parseTimeline } from "./parseTimeline";

const validTimeline = {
  chunks: [
    { start: 0, end: 3.2, tone: "NEUTRAL", score: 5, color: "#CCCCCC", text: "Hi" },
  ],
  overall: { score: 5, tone: "NEUTRAL" },
};

describe("parseTimeline", () => {
  it("parses valid JSON string into a SentimentTimeline", () => {
    const result = parseTimeline(JSON.stringify(validTimeline));
    expect(result.chunks).toHaveLength(1);
    expect(result.overall.score).toBe(5);
  });

  it("throws on invalid JSON", () => {
    expect(() => parseTimeline("not json")).toThrow("Invalid JSON");
  });

  it("throws when chunks field is missing", () => {
    const bad = JSON.stringify({ overall: { score: 5, tone: "NEUTRAL" } });
    expect(() => parseTimeline(bad)).toThrow("Invalid sentiment timeline");
  });

  it("throws when overall field is missing", () => {
    const bad = JSON.stringify({ chunks: [] });
    expect(() => parseTimeline(bad)).toThrow("Invalid sentiment timeline");
  });

  it("throws when top level is an array instead of object", () => {
    expect(() => parseTimeline("[]")).toThrow("Invalid sentiment timeline");
  });

  it("throws when top level is null", () => {
    expect(() => parseTimeline("null")).toThrow("Invalid sentiment timeline");
  });

  it("throws on empty string", () => {
    expect(() => parseTimeline("")).toThrow();
  });

  it("preserves all chunk fields", () => {
    const result = parseTimeline(JSON.stringify(validTimeline));
    expect(result.chunks[0]).toMatchObject({
      start: 0,
      end: 3.2,
      tone: "NEUTRAL",
      score: 5,
      color: "#CCCCCC",
      text: "Hi",
    });
  });
});
