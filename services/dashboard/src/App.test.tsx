import { describe, it, expect, vi } from "vitest";
import { render, screen, act, fireEvent } from "@testing-library/react";
import { App } from "./App";
import { SentimentTimeline } from "./types/sentiment";

const sampleTimeline: SentimentTimeline = {
  chunks: [
    {
      start: 0.0, end: 3.2, tone: "SLIGHTLY_POSITIVE", score: 6, color: "#90EE90", text: "Hello.",
      anger_level: 0,
      frustration_level: 0,
      sarcasm_flag: false
    },
    {
      start: 3.2, end: 7.5, tone: "POSITIVE", score: 8, color: "#32CD32", text: "Great news.",
      anger_level: 0,
      frustration_level: 0,
      sarcasm_flag: false
    },
  ],
  overall: { score: 7.0, tone: "POSITIVE" },
};

/** Helper: simulate a successful file load by triggering the FileUpload's onLoad path */
function loadTimeline() {
  const readAsText = vi.fn();
  const mockReader = { onload: null as unknown, readAsText };
  vi.spyOn(window, "FileReader").mockImplementation(() => mockReader as unknown as FileReader);

  const input = screen.getByTestId("file-input");

  fireEvent.change(input, {
    target: { files: [new File([JSON.stringify(sampleTimeline)], "timeline.json")] },
  });

  act(() => {
    (mockReader as { onload: (e: { target: { result: string } }) => void }).onload({
      target: { result: JSON.stringify(sampleTimeline) },
    });
  });
}

describe("App — initial state", () => {
  it("renders the page heading", () => {
    render(<App />);
    expect(screen.getByText(/Video Sentiment Dashboard/i)).toBeInTheDocument();
  });

  it("shows the full pipeline uploader", () => {
    render(<App />);
    expect(screen.getByTestId("pipeline-upload")).toBeInTheDocument();
    expect(screen.getByTestId("transcript-input")).toBeInTheDocument();
    expect(screen.getByTestId("video-input")).toBeInTheDocument();
  });

  it("shows the FileUpload component before any file is loaded", () => {
    render(<App />);
    expect(screen.getByTestId("file-upload")).toBeInTheDocument();
  });

  it("does not show charts before a file is loaded", () => {
    render(<App />);
    expect(screen.queryByTestId("chunk-timeline")).not.toBeInTheDocument();
    expect(screen.queryByTestId("sentiment-chart")).not.toBeInTheDocument();
  });

  it("does not show the inspector before a file is loaded", () => {
    render(<App />);
    expect(screen.queryByTestId("chunk-inspector")).not.toBeInTheDocument();
    expect(screen.queryByTestId("chunk-inspector-empty")).not.toBeInTheDocument();
  });
});

describe("App — after file loaded", () => {
  it("hides the FileUpload and shows charts", () => {
    render(<App />);
    loadTimeline();
    expect(screen.queryByTestId("file-upload")).not.toBeInTheDocument();
    expect(screen.getByTestId("chunk-timeline")).toBeInTheDocument();
    expect(screen.getByTestId("sentiment-chart")).toBeInTheDocument();
  });

  it("shows the empty inspector initially (no chunk selected)", () => {
    render(<App />);
    loadTimeline();
    expect(screen.getByTestId("chunk-inspector-empty")).toBeInTheDocument();
  });

  it("displays the loaded filename", () => {
    render(<App />);
    loadTimeline();
    expect(screen.getByText(/timeline\.json/)).toBeInTheDocument();
  });

  it("displays the overall tone and score", () => {
    render(<App />);
    loadTimeline();
    expect(screen.getByText(/overall positive 7\/10/i)).toBeInTheDocument();
  });

  it("shows the chunk inspector when a chunk is clicked", () => {
    render(<App />);
    loadTimeline();
    const chunkButton = screen.getByTestId("chunk-button-0");
    fireEvent.click(chunkButton);
    expect(screen.getByTestId("chunk-inspector")).toBeInTheDocument();
  }); 
  it("sets the playhead when a chunk is clicked", () => {
    const setPlayheadMock = vi.fn();
    render(<App />);
    loadTimeline();
    const chunkButton = screen.getByTestId("chunk-button-0");
    fireEvent.click(chunkButton);
    expect(setPlayheadMock).toHaveBeenCalledWith(0.0);
  });
  it("shows a 'Load another file' button after load", () => {
    render(<App />);
    loadTimeline();
    expect(screen.getByText(/load another file/i)).toBeInTheDocument();
  });
});
