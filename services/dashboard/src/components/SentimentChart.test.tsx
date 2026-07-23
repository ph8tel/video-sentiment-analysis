import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { SentimentChart } from "./SentimentChart";
import { ScoredChunk, OverallScore } from "../types/sentiment";

const chunks: ScoredChunk[] = [
  { start: 0.0, end: 3.2, tone: "SLIGHTLY_POSITIVE", score: 6, color: "#90EE90", text: "Hello." },
  { start: 3.2, end: 7.5, tone: "POSITIVE",          score: 8, color: "#32CD32", text: "Great." },
  { start: 7.5, end: 12.1, tone: "NEGATIVE",         score: 2, color: "#FF4500", text: "Bad." },
];

const overall: OverallScore = { score: 5.7, tone: "SLIGHTLY_POSITIVE" };

describe("SentimentChart", () => {
  it("renders without crashing", () => {
    render(<SentimentChart chunks={chunks} overall={overall} />);
    expect(screen.getByTestId("sentiment-chart")).toBeInTheDocument();
  });

  it("renders the section heading", () => {
    render(<SentimentChart chunks={chunks} overall={overall} />);
    expect(screen.getByText("Sentiment Trend")).toBeInTheDocument();
  });

  it("renders with a single chunk", () => {
    render(<SentimentChart chunks={[chunks[0]]} overall={overall} />);
    expect(screen.getByTestId("sentiment-chart")).toBeInTheDocument();
  });

  it("renders with an empty chunk array", () => {
    render(<SentimentChart chunks={[]} overall={overall} />);
    expect(screen.getByTestId("sentiment-chart")).toBeInTheDocument();
  });

  it("does not throw with extreme scores", () => {
    const extremes: ScoredChunk[] = [
      { ...chunks[0], score: 0 },
      { ...chunks[1], score: 10 },
    ];
    expect(() =>
      render(<SentimentChart chunks={extremes} overall={overall} />)
    ).not.toThrow();
  });
});
