import { useCallback, useState } from "react";
import { MediaIngestChunk, MediaIngestResult, MultiSpeakerTimelines, SentimentTimeline } from "../types/sentiment";

interface Props {
    onComplete: (timelines: MultiSpeakerTimelines, renderedVideo: Blob, sourceName: string) => void;
    onError: (message: string) => void;
}

const MEDIA_INGEST_URL =
    (import.meta.env.VITE_MEDIA_INGEST_URL as string | undefined) ?? "http://localhost:8003";
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

function stripSpeaker(chunks: MediaIngestChunk[]): { start: number; end: number; text: string }[] {
    return chunks.map(({ start, end, text }) => ({ start, end, text }));
}

async function scoreChunks(chunks: { start: number; end: number; text: string }[]): Promise<SentimentTimeline> {
    const resp = await fetch(`${SCORING_URL}/score`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(chunks),
    });
    if (!resp.ok) {
        throw new Error(`Scoring failed (${resp.status}): ${parseApiError(await resp.text())}`);
    }
    return (await resp.json()) as SentimentTimeline;
}

export function VideoUpload({ onComplete, onError }: Props) {
    const [videoFile, setVideoFile] = useState<File | null>(null);
    const [dragging, setDragging] = useState(false);
    const [busy, setBusy] = useState(false);
    const [status, setStatus] = useState("");

    const runPipeline = useCallback(async () => {
        if (!videoFile) {
            onError("Please provide an MP4 video file with two speakers.");
            return;
        }
        if (!videoFile.name.toLowerCase().endsWith(".mp4")) {
            onError("Video must be an .mp4 file.");
            return;
        }

        setBusy(true);
        onError("");

        try {
            setStatus("Transcribing and diarizing speakers...");
            const ingestForm = new FormData();
            ingestForm.append("video", videoFile);
            const ingestResp = await fetch(`${MEDIA_INGEST_URL}/ingest`, {
                method: "POST",
                body: ingestForm,
            });
            if (!ingestResp.ok) {
                throw new Error(`Ingest failed (${ingestResp.status}): ${parseApiError(await ingestResp.text())}`);
            }
            const ingestResult = (await ingestResp.json()) as MediaIngestResult;

            if (!ingestResult.chunks.length) {
                throw new Error("No speech was detected in the video.");
            }

            const [leftSpeaker, rightSpeaker] = ingestResult.speaker_order;
            const leftChunks = stripSpeaker(ingestResult.chunks.filter((c) => c.speaker === leftSpeaker));
            const rightChunks = rightSpeaker
                ? stripSpeaker(ingestResult.chunks.filter((c) => c.speaker === rightSpeaker))
                : [];
            const overallChunks = stripSpeaker(ingestResult.chunks);

            setStatus("Scoring overall sentiment...");
            const overall = await scoreChunks(overallChunks);

            setStatus("Scoring per-speaker sentiment...");
            const speakerLeft = leftChunks.length ? await scoreChunks(leftChunks) : null;
            const speakerRight = rightChunks.length ? await scoreChunks(rightChunks) : null;

            setStatus("Rendering overlay video...");
            const renderForm = new FormData();
            renderForm.append("video", videoFile);
            renderForm.append("overall_timeline", JSON.stringify(overall.chunks));
            renderForm.append("speaker_left_timeline", JSON.stringify(speakerLeft?.chunks ?? []));
            renderForm.append("speaker_right_timeline", JSON.stringify(speakerRight?.chunks ?? []));

            const renderResp = await fetch(`${FFMPEG_URL}/render-multi`, {
                method: "POST",
                body: renderForm,
            });
            if (!renderResp.ok) {
                throw new Error(`Render failed (${renderResp.status}): ${parseApiError(await renderResp.text())}`);
            }
            const renderedVideo = await renderResp.blob();

            onComplete({ overall, speakerLeft, speakerRight }, renderedVideo, videoFile.name);
            setStatus("Done.");
        } catch (err) {
            onError(err instanceof Error ? err.message : "Pipeline failed.");
            setStatus("");
        } finally {
            setBusy(false);
        }
    }, [onComplete, onError, videoFile]);

    return (
        <div
            data-testid="video-upload"
            style={{ border: "1px solid #d8deea", borderRadius: 12, padding: 16, background: "#ffffff" }}
        >
            <h2 style={{ margin: "0 0 4px", fontSize: 17 }}>Two-Speaker Video</h2>
            <p style={{ margin: "0 0 14px", color: "#56637a", fontSize: 13 }}>
                Drop an MP4 of two people talking. The dashboard will transcribe, diarize, score
                overall + per-speaker sentiment, and render a 3-position emoji overlay.
            </p>

            <label
                onDrop={(e) => {
                    e.preventDefault();
                    setDragging(false);
                    const file = e.dataTransfer.files?.[0];
                    if (file) setVideoFile(file);
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
                <div style={{ fontSize: 13, fontWeight: 700, color: "#273449" }}>Video</div>
                <div style={{ marginTop: 6, fontSize: 13, color: "#516076" }}>.mp4, two speakers</div>
                <input
                    data-testid="two-speaker-video-input"
                    type="file"
                    accept="video/mp4,.mp4"
                    style={{ marginTop: 12 }}
                    onChange={(e) => {
                        const file = e.target.files?.[0];
                        if (file) setVideoFile(file);
                    }}
                />
            </label>

            <div style={{ marginTop: 12, display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
                <button
                    data-testid="run-video-pipeline"
                    onClick={() => {
                        void runPipeline();
                    }}
                    disabled={busy || !videoFile}
                    style={{
                        border: "none",
                        borderRadius: 8,
                        padding: "10px 14px",
                        background: busy || !videoFile ? "#9ba8bf" : "#0a7f5a",
                        color: "white",
                        cursor: busy || !videoFile ? "not-allowed" : "pointer",
                        fontWeight: 700,
                    }}
                >
                    {busy ? "Working..." : "Ingest + Score + Render"}
                </button>

                <span style={{ color: "#5b677c", fontSize: 13 }}>
                    {videoFile ? `Video: ${videoFile.name}` : "Video: none"}
                </span>
            </div>

            {status && (
                <p data-testid="video-pipeline-status" style={{ marginTop: 10, color: "#2d3a50", fontSize: 13 }}>
                    {status}
                </p>
            )}
        </div>
    );
}
