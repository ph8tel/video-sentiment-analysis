import { useState } from "react";
import { SentimentTimeline, ScoredChunk } from "./types/sentiment";
import { FileUpload } from "./components/FileUpload";
import { ChunkTimeline } from "./components/ChunkTimeline";
import { SentimentChart } from "./components/SentimentChart";
import { ChunkInspector } from "./components/ChunkInspector";

export function App() {
  const [timeline, setTimeline] = useState<SentimentTimeline | null>(null);
  const [filename, setFilename] = useState("");
  const [selectedChunk, setSelectedChunk] = useState<ScoredChunk | null>(null);
  const [error, setError] = useState("");

  const handleLoad = (data: SentimentTimeline, name: string) => {
    setTimeline(data);
    setFilename(name);
    setSelectedChunk(null);
    setError("");
  };

  const handleReset = () => {
    setTimeline(null);
    setFilename("");
    setSelectedChunk(null);
    setError("");
  };

  return (
    <div
      style={{
        fontFamily: "system-ui, sans-serif",
        maxWidth: 1200,
        margin: "0 auto",
        padding: "24px 16px",
      }}
    >
      <h1 style={{ margin: "0 0 4px", fontSize: 22 }}>
        Video Sentiment Dashboard
      </h1>

      {timeline ? (
        <p style={{ color: "#666", marginTop: 4, fontSize: 14 }}>
          Loaded: <strong>{filename}</strong> ({timeline.chunks.length} chunks
          — overall {timeline.overall.tone.replace(/_/g, " ")} {timeline.overall.score}/10){" "}
          <button
            onClick={handleReset}
            style={{
              background: "none",
              border: "none",
              color: "#0066cc",
              cursor: "pointer",
              padding: 0,
              fontSize: 14,
            }}
          >
            Load another file
          </button>
        </p>
      ) : (
        <div style={{ marginTop: 16 }}>
          <FileUpload onLoad={handleLoad} onError={setError} />
          {error && (
            <p
              data-testid="upload-error"
              style={{ color: "#cc0000", marginTop: 8, fontSize: 14 }}
            >
              {error}
            </p>
          )}
        </div>
      )}

      {timeline && (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 300px",
            gap: 24,
            marginTop: 24,
          }}
        >
          <div>
            <ChunkTimeline
              chunks={timeline.chunks}
              selectedChunk={selectedChunk}
              onChunkClick={setSelectedChunk}
            />
            <div style={{ marginTop: 24 }}>
              <SentimentChart chunks={timeline.chunks} overall={timeline.overall} />
            </div>
          </div>
          <div
            style={{
              background: "#fff",
              border: "1px solid #e0e0e0",
              borderRadius: 8,
              alignSelf: "start",
            }}
          >
            <ChunkInspector chunk={selectedChunk} />
          </div>
        </div>
      )}
    </div>
  );
}
