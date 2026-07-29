import { useCallback, useState } from "react";
import { SentimentTimeline } from "../types/sentiment";
import { parseTranscript } from "../utils/parseTranscript";

interface Props {
  onComplete: (timeline: SentimentTimeline, renderedVideo: Blob, sourceName: string) => void;
  onError: (message: string) => void;
}

const SCORING_URL =
  (import.meta.env.VITE_SCORING_URL as string | undefined) ?? "http://localhost:8002";
const FFMPEG_URL =
  (import.meta.env.VITE_FFMPEG_URL as string | undefined) ?? "http://localhost:8001";

function parseApiError(body: string): string {
  try {
    const parsed = JSON.parse(body) as { detail?: string };
    return parsed.detail ?? body;
  } catch {
    return body;
  }
}

function DropFileInput({
  label,
  hint,
  accept,
  testId,
  onFile,
}: {
  label: string;
  hint: string;
  accept: string;
  testId: string;
  onFile: (file: File) => void;
}) {
  const [dragging, setDragging] = useState(false);

  return (
    <label
      onDrop={(e) => {
        e.preventDefault();
        setDragging(false);
        const file = e.dataTransfer.files?.[0];
        if (file) {
          onFile(file);
        }
      }}
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      style={{
        display: "block",
        border: `2px dashed ${dragging ? "#1f8f6f" : "#b9c2cf"}`,
        borderRadius: 10,
        padding: "16px 14px",
        background: dragging ? "#f1fffa" : "#fbfcff",
        cursor: "pointer",
      }}
    >
      <div style={{ fontSize: 13, fontWeight: 700, color: "#273449" }}>{label}</div>
      <div style={{ marginTop: 6, fontSize: 13, color: "#516076" }}>{hint}</div>
      <input
        data-testid={testId}
        type="file"
        accept={accept}
        style={{ marginTop: 12 }}
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) {
            onFile(file);
          }
        }}
      />
    </label>
  );
}

export function PipelineUpload({ onComplete, onError }: Props) {
  const [transcriptFile, setTranscriptFile] = useState<File | null>(null);
  const [videoFile, setVideoFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState("");

  const runPipeline = useCallback(async () => {
    if (!transcriptFile || !videoFile) {
      onError("Please provide both a transcript file and an MP4 video file.");
      return;
    }

    if (!videoFile.name.toLowerCase().endsWith(".mp4")) {
      onError("Video must be an .mp4 file.");
      return;
    }

    setBusy(true);
    setStatus("Parsing transcript...");
    onError("");

    try {
      const transcriptRaw = await transcriptFile.text();
      const chunks = parseTranscript(transcriptRaw);

      setStatus("Scoring transcript with Ollama...");
      const scoreResp = await fetch(`${SCORING_URL}/score`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(chunks),
      });

      if (!scoreResp.ok) {
        throw new Error(`Scoring failed (${scoreResp.status}): ${parseApiError(await scoreResp.text())}`);
      }

      const timeline = (await scoreResp.json()) as SentimentTimeline;

      setStatus("Rendering overlay video...");
      const formData = new FormData();
      formData.append("video", videoFile);
      formData.append("timeline", JSON.stringify(timeline.chunks));

      const renderResp = await fetch(`${FFMPEG_URL}/render`, {
        method: "POST",
        body: formData,
      });

      if (!renderResp.ok) {
        throw new Error(`Render failed (${renderResp.status}): ${parseApiError(await renderResp.text())}`);
      }

      const renderedVideo = await renderResp.blob();
      onComplete(timeline, renderedVideo, transcriptFile.name);
      setStatus("Done.");
    } catch (err) {
      onError(err instanceof Error ? err.message : "Pipeline failed.");
      setStatus("");
    } finally {
      setBusy(false);
    }
  }, [onComplete, onError, transcriptFile, videoFile]);

  return (
    <div
      data-testid="pipeline-upload"
      style={{ border: "1px solid #d8deea", borderRadius: 12, padding: 16, background: "#ffffff" }}
    >
      <h2 style={{ margin: "0 0 4px", fontSize: 17 }}>Run Full Pipeline</h2>
      <p style={{ margin: "0 0 14px", color: "#56637a", fontSize: 13 }}>
        Drop a transcript and matching MP4. The dashboard will call /score, then /render,
        and preview the rendered video.
      </p>

      <div style={{ display: "grid", gap: 12, gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))" }}>
        <DropFileInput
          label="Transcript"
          hint=".json transcript array or raw timestamp blocks"
          accept=".json,.txt,.text"
          testId="transcript-input"
          onFile={setTranscriptFile}
        />
        <DropFileInput
          label="Video"
          hint=".mp4 source video"
          accept="video/mp4,.mp4"
          testId="video-input"
          onFile={setVideoFile}
        />
      </div>

      <div style={{ marginTop: 12, display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
        <button
          data-testid="run-pipeline"
          onClick={() => {
            void runPipeline();
          }}
          disabled={busy || !transcriptFile || !videoFile}
          style={{
            border: "none",
            borderRadius: 8,
            padding: "10px 14px",
            background: busy || !transcriptFile || !videoFile ? "#9ba8bf" : "#0a7f5a",
            color: "white",
            cursor: busy || !transcriptFile || !videoFile ? "not-allowed" : "pointer",
            fontWeight: 700,
          }}
        >
          {busy ? "Working..." : "Score + Render"}
        </button>

        <span style={{ color: "#5b677c", fontSize: 13 }}>
          {transcriptFile ? `Transcript: ${transcriptFile.name}` : "Transcript: none"}
        </span>
        <span style={{ color: "#5b677c", fontSize: 13 }}>
          {videoFile ? `Video: ${videoFile.name}` : "Video: none"}
        </span>
      </div>

      {status && (
        <p data-testid="pipeline-status" style={{ marginTop: 10, color: "#2d3a50", fontSize: 13 }}>
          {status}
        </p>
      )}
    </div>
  );
}