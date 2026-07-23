import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { ChunkTimeline } from "./ChunkTimeline";
import { ScoredChunk } from "../types/sentiment";

const chunks: ScoredChunk[] = [
  { start: 0.0, end: 3.2, tone: "SLIGHTLY_POSITIVE", score: 6, color: "#90EE90", text: "Hello." },
  { start: 3.2, end: 7.5, tone: "POSITIVE",          score: 8, color: "#32CD32", text: "Great." },
  { start: 7.5, end: 12.1, tone: "NEGATIVE",         score: 2, color: "#FF4500", text: "Bad." },
];

describe("ChunkTimeline", () => {
  it("renders without crashing", () => {
    render(<ChunkTimeline chunks={chunks} selectedChunk={null} onChunkClick={vi.fn()} />);
    expect(screen.getByTestId("chunk-timeline")).toBeInTheDocument();
  });

  it("renders the section heading", () => {
    render(<ChunkTimeline chunks={chunks} selectedChunk={null} onChunkClick={vi.fn()} />);
    expect(screen.getByText("Chunk Sentiment")).toBeInTheDocument();
  });

  it("renders with a single chunk", () => {
    render(
      <ChunkTimeline chunks={[chunks[0]]} selectedChunk={null} onChunkClick={vi.fn()} />
    );
    expect(screen.getByTestId("chunk-timeline")).toBeInTheDocument();
  });

  it("renders with an empty chunk array", () => {
    render(<ChunkTimeline chunks={[]} selectedChunk={null} onChunkClick={vi.fn()} />);
    expect(screen.getByTestId("chunk-timeline")).toBeInTheDocument();
  });

  it("does not throw when a chunk is selected", () => {
    expect(() =>
      render(
        <ChunkTimeline chunks={chunks} selectedChunk={chunks[1]} onChunkClick={vi.fn()} />
      )
    ).not.toThrow();
  });
});
