import { describe, expect, it } from "vitest";
import { parseTranscript } from "./parseTranscript";

describe("parseTranscript", () => {
  it("parses transcript JSON input", () => {
    const raw = JSON.stringify([
      { start: 0, end: 2.5, text: "Hello" },
      { start: 2.5, end: 5, text: "World" },
    ]);

    expect(parseTranscript(raw)).toEqual([
      { start: 0, end: 2.5, text: "Hello" },
      { start: 2.5, end: 5, text: "World" },
    ]);
  });

  it("parses timestamp block transcript input", () => {
    const raw = [
      "0:03",
      "3 seconds",
      "first chunk",
      "0:10",
      "10 seconds",
      "second chunk",
      "0:23",
      "23 seconds",
      "third chunk",
    ].join("\n");

    expect(parseTranscript(raw)).toEqual([
      { start: 3, end: 10, text: "first chunk" },
      { start: 10, end: 23, text: "second chunk" },
      { start: 23, end: 36, text: "third chunk" },
    ]);
  });

  it("throws on empty input", () => {
    expect(() => parseTranscript("   ")).toThrow("Transcript file is empty.");
  });
});