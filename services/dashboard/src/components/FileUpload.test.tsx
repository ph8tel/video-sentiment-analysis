import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { FileUpload } from "./FileUpload";

const onLoad = vi.fn();
const onError = vi.fn();

beforeEach(() => {
  vi.clearAllMocks();
});

describe("FileUpload", () => {
  it("renders the drop zone", () => {
    render(<FileUpload onLoad={onLoad} onError={onError} />);
    expect(screen.getByTestId("file-upload")).toBeInTheDocument();
  });

  it("renders a file input", () => {
    render(<FileUpload onLoad={onLoad} onError={onError} />);
    expect(screen.getByTestId("file-input")).toBeInTheDocument();
  });

  it("file input only accepts .json", () => {
    render(<FileUpload onLoad={onLoad} onError={onError} />);
    expect(screen.getByTestId("file-input")).toHaveAttribute("accept", ".json");
  });

  it("shows the drop zone hint text", () => {
    render(<FileUpload onLoad={onLoad} onError={onError} />);
    expect(screen.getByText(/sentiment_timeline\.json/)).toBeInTheDocument();
  });

  it("calls onError when a non-JSON file is selected", () => {
    render(<FileUpload onLoad={onLoad} onError={onError} />);
    const input = screen.getByTestId("file-input");
    const file = new File(["content"], "video.mp4", { type: "video/mp4" });
    fireEvent.change(input, { target: { files: [file] } });
    expect(onError).toHaveBeenCalledWith("Please select a .json file.");
    expect(onLoad).not.toHaveBeenCalled();
  });

  it("calls onLoad with parsed data when a valid JSON file is selected", async () => {
    const timeline = {
      chunks: [{ start: 0, end: 1, tone: "NEUTRAL", score: 5, color: "#CCCCCC", text: "Hi" }],
      overall: { score: 5, tone: "NEUTRAL" },
    };

    // Stub FileReader to synchronously fire onload
    const readAsText = vi.fn();
    const mockReader = { onload: null as unknown, readAsText };
    vi.spyOn(window, "FileReader").mockImplementation(() => mockReader as unknown as FileReader);

    render(<FileUpload onLoad={onLoad} onError={onError} />);
    const input = screen.getByTestId("file-input");
    const file = new File([JSON.stringify(timeline)], "timeline.json", { type: "application/json" });

    fireEvent.change(input, { target: { files: [file] } });

    // Simulate FileReader completing
    (mockReader as { onload: (e: { target: { result: string } }) => void }).onload({
      target: { result: JSON.stringify(timeline) },
    });

    expect(onLoad).toHaveBeenCalledWith(expect.objectContaining({ chunks: expect.any(Array) }), "timeline.json");
    expect(onError).not.toHaveBeenCalled();
  });

  it("calls onError when JSON file has invalid shape", async () => {
    const readAsText = vi.fn();
    const mockReader = { onload: null as unknown, readAsText };
    vi.spyOn(window, "FileReader").mockImplementation(() => mockReader as unknown as FileReader);

    render(<FileUpload onLoad={onLoad} onError={onError} />);
    const input = screen.getByTestId("file-input");
    const file = new File(['{"wrong":true}'], "bad.json", { type: "application/json" });

    fireEvent.change(input, { target: { files: [file] } });
    (mockReader as { onload: (e: { target: { result: string } }) => void }).onload({
      target: { result: '{"wrong":true}' },
    });

    expect(onError).toHaveBeenCalled();
    expect(onLoad).not.toHaveBeenCalled();
  });
});
