import { useEffect, useState } from "react";
import { SentimentTimeline, ScoredChunk } from "./types/sentiment";
import { FileUpload } from "./components/FileUpload";
import { PipelineUpload } from "./components/PipelineUpload";
import { ChunkTimeline } from "./components/ChunkTimeline";
import { SentimentChart } from "./components/SentimentChart";
import { EmotionChart } from "./components/EmotionChart";
import { ChunkInspector } from "./components/ChunkInspector";

export function App() {
  const [timeline, setTimeline] = useState<SentimentTimeline | null>(null);
  const [filename, setFilename] = useState("");
  const [selectedChunk, setSelectedChunk] = useState<ScoredChunk | null>(null);
  const [error, setError] = useState("");
  const [renderedVideoUrl, setRenderedVideoUrl] = useState<string | null>(null);

  const handleLoad = (data: SentimentTimeline, name: string) => {
    if (renderedVideoUrl) {
      URL.revokeObjectURL(renderedVideoUrl);
    }
    setTimeline(data);
    setFilename(name);
    setSelectedChunk(null);
    setRenderedVideoUrl(null);
    setError("");
  };

  const handlePipelineComplete = (data: SentimentTimeline, video: Blob, sourceName: string) => {
    if (renderedVideoUrl) {
      URL.revokeObjectURL(renderedVideoUrl);
    }
    const url = URL.createObjectURL(video);
    setTimeline(data);
    setFilename(`Generated from ${sourceName}`);
    setSelectedChunk(null);
    setRenderedVideoUrl(url);
    setError("");
  };

  const handleReset = () => {
    if (renderedVideoUrl) {
      URL.revokeObjectURL(renderedVideoUrl);
    }
    setTimeline(null);
    setFilename("");
    setSelectedChunk(null);
    setRenderedVideoUrl(null);
    setError("");
  };

  useEffect(() => {
    return () => {
      if (renderedVideoUrl) {
        URL.revokeObjectURL(renderedVideoUrl);
      }
    };
  }, [renderedVideoUrl]);

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
        <div style={{ marginTop: 16, display: "grid", gap: 16 }}>
          <PipelineUpload onComplete={handlePipelineComplete} onError={setError} />

          <div
            style={{
              border: "1px solid #dfe4ef",
              borderRadius: 12,
              padding: 16,
              background: "#ffffff",
            }}
          >
            <h2 style={{ margin: "0 0 4px", fontSize: 17 }}>Load Existing Timeline</h2>
            <p style={{ margin: "0 0 12px", color: "#56637a", fontSize: 13 }}>
              Already have sentiment_timeline.json? Load it directly to inspect chunks.
            </p>
          <FileUpload onLoad={handleLoad} onError={setError} />
          </div>

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
        <>
          {renderedVideoUrl && (
            <div
              style={{
                marginTop: 20,
                border: "1px solid #dde3ef",
                borderRadius: 10,
                padding: 12,
                background: "#fff",
              }}
            >
              <h2 style={{ margin: "4px 0 12px", fontSize: 18 }}>Rendered Video</h2>
              <video
                data-testid="rendered-video"
                controls
                src={renderedVideoUrl}
                style={{ width: "100%", maxWidth: 840, borderRadius: 8, background: "#000" }}
              />
              <p style={{ marginTop: 8, fontSize: 13 }}>
                <a href={renderedVideoUrl} download="video_with_overlay.mp4">
                  Download rendered video
                </a>
              </p>
            </div>
          )}

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
              <div style={{ marginTop: 24 }}>
                <EmotionChart chunks={timeline.chunks} />
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
        </>
      )}
    </div>
  );
}
