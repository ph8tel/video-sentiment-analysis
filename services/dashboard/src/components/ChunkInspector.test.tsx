import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ChunkInspector } from "./ChunkInspector";
import { ScoredChunk } from "../types/sentiment";

const chunk: ScoredChunk = {
  start: 12.4,
  end: 15.8,
  tone: "NEGATIVE",
  score: 2,
  color: "#FF4500",
  text: "Unfortunately there were setbacks.",
};

describe("ChunkInspector — empty state", () => {
  it("renders when no chunk is selected", () => {
    render(<ChunkInspector chunk={null} />);
    expect(screen.getByTestId("chunk-inspector-empty")).toBeInTheDocument();
  });

  it("shows a prompt to click a chunk", () => {
    render(<ChunkInspector chunk={null} />);
    expect(screen.getByText(/click a chunk/i)).toBeInTheDocument();
  });

  it("does not render the detail table", () => {
    render(<ChunkInspector chunk={null} />);
    expect(screen.queryByTestId("chunk-inspector")).not.toBeInTheDocument();
  });
});

describe("ChunkInspector — with chunk", () => {
  it("renders the inspector panel", () => {
    render(<ChunkInspector chunk={chunk} />);
    expect(screen.getByTestId("chunk-inspector")).toBeInTheDocument();
  });

  it("does not render the empty state", () => {
    render(<ChunkInspector chunk={chunk} />);
    expect(screen.queryByTestId("chunk-inspector-empty")).not.toBeInTheDocument();
  });

  it("displays start and end time", () => {
    render(<ChunkInspector chunk={chunk} />);
    expect(screen.getByTestId("chunk-time")).toHaveTextContent("12.40s – 15.80s");
  });

  it("displays tone", () => {
    render(<ChunkInspector chunk={chunk} />);
    expect(screen.getByTestId("chunk-tone")).toHaveTextContent("NEGATIVE");
  });

  it("displays score out of 10", () => {
    render(<ChunkInspector chunk={chunk} />);
    expect(screen.getByTestId("chunk-score")).toHaveTextContent("2 / 10");
  });

  it("displays hex color value", () => {
    render(<ChunkInspector chunk={chunk} />);
    expect(screen.getByTestId("chunk-color")).toHaveTextContent("#FF4500");
  });

  it("renders the color swatch with correct background", () => {
    render(<ChunkInspector chunk={chunk} />);
    const swatch = screen.getByTestId("chunk-color-swatch");
    expect(swatch).toHaveStyle({ background: "#FF4500" });
  });

  it("displays the chunk text", () => {
    render(<ChunkInspector chunk={chunk} />);
    expect(screen.getByTestId("chunk-text")).toHaveTextContent(chunk.text);
  });

  it("updates when a different chunk is passed", () => {
    const { rerender } = render(<ChunkInspector chunk={chunk} />);
    const otherChunk: ScoredChunk = { ...chunk, tone: "VERY_POSITIVE", score: 10, color: "#008000" };
    rerender(<ChunkInspector chunk={otherChunk} />);
    expect(screen.getByTestId("chunk-tone")).toHaveTextContent("VERY_POSITIVE");
    expect(screen.getByTestId("chunk-score")).toHaveTextContent("10 / 10");
  });

  it("transitions back to empty state when chunk becomes null", () => {
    const { rerender } = render(<ChunkInspector chunk={chunk} />);
    rerender(<ChunkInspector chunk={null} />);
    expect(screen.getByTestId("chunk-inspector-empty")).toBeInTheDocument();
  });
});
