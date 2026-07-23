import { useCallback, useState } from "react";
import { SentimentTimeline } from "../types/sentiment";
import { parseTimeline } from "../utils/parseTimeline";

interface Props {
  onLoad: (timeline: SentimentTimeline, filename: string) => void;
  onError: (message: string) => void;
}

export function FileUpload({ onLoad, onError }: Props) {
  const [dragging, setDragging] = useState(false);

  const processFile = useCallback(
    (file: File) => {
      if (!file.name.endsWith(".json")) {
        onError("Please select a .json file.");
        return;
      }
      const reader = new FileReader();
      reader.onload = (e) => {
        try {
          const timeline = parseTimeline(e.target?.result as string);
          onLoad(timeline, file.name);
        } catch (err) {
          onError(err instanceof Error ? err.message : "Failed to read file.");
        }
      };
      reader.readAsText(file);
    },
    [onLoad, onError]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      const file = e.dataTransfer.files[0];
      if (file) processFile(file);
    },
    [processFile]
  );

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) processFile(file);
    },
    [processFile]
  );

  return (
    <div
      data-testid="file-upload"
      onDrop={handleDrop}
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      style={{
        border: `2px dashed ${dragging ? "#4CAF50" : "#ccc"}`,
        borderRadius: 8,
        padding: "40px 24px",
        textAlign: "center",
        background: dragging ? "#f0fff0" : "#fafafa",
        transition: "border-color 0.15s, background 0.15s",
      }}
    >
      <p style={{ margin: "0 0 12px", color: "#555" }}>
        Drop <code>sentiment_timeline.json</code> here, or browse:
      </p>
      <input
        type="file"
        accept=".json"
        onChange={handleChange}
        data-testid="file-input"
      />
    </div>
  );
}
