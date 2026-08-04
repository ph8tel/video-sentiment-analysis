import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { ChunkTimeline } from "./ChunkTimeline";
import { ScoredChunk } from "../types/sentiment";

const chunks: ScoredChunk[] = [
  {
    start: 0.0, end: 3.2, tone: "SLIGHTLY_POSITIVE", score: 6, color: "#90EE90", text: "Hello.",
    anger_level: 0,
    frustration_level: 0,
    sarcasm_flag: false
  },
  {
    start: 3.2, end: 7.5, tone: "POSITIVE", score: 8, color: "#32CD32", text: "Great.",
    anger_level: 0,
    frustration_level: 0,
    sarcasm_flag: false
  },
  {
    start: 7.5, end: 12.1, tone: "NEGATIVE", score: 2, color: "#FF4500", text: "Bad.",
    anger_level: 0,
    frustration_level: 0,
    sarcasm_flag: false
  },
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

  it("renders a custom title when provided", () => {
    render(<ChunkTimeline chunks={chunks} selectedChunk={null} onChunkClick={vi.fn()} title="Speaker 1" />);
    expect(screen.getByText("Speaker 1")).toBeInTheDocument();
  });

  it("uses a unique testid derived from a custom title", () => {
    render(<ChunkTimeline chunks={chunks} selectedChunk={null} onChunkClick={vi.fn()} title="Speaker 1" />);
    expect(screen.getByTestId("chunk-timeline-speaker-1")).toBeInTheDocument();
  });

  it("allows two ChunkTimeline instances with different titles to coexist", () => {
    render(
      <>
        <ChunkTimeline chunks={chunks} selectedChunk={null} onChunkClick={vi.fn()} />
        <ChunkTimeline chunks={chunks} selectedChunk={null} onChunkClick={vi.fn()} title="Speaker 2" />
      </>
    );
    expect(screen.getByTestId("chunk-timeline")).toBeInTheDocument();
    expect(screen.getByTestId("chunk-timeline-speaker-2")).toBeInTheDocument();
  });
});
