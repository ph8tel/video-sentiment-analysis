import { ScoredChunk } from "../types/sentiment";

const ANGER_EMOJI = ["😐", "😠", "😡", "💥"] as const;
const FRUSTRATION_EMOJI = ["😐", "😤", "😣", "🤬"] as const;

interface Props {
  chunk: ScoredChunk | null;
}

export function ChunkInspector({ chunk }: Props) {
  if (!chunk) {
    return (
      <div
        data-testid="chunk-inspector-empty"
        style={{ padding: 16, color: "#888", fontStyle: "italic" }}
      >
        Click a chunk to inspect it.
      </div>
    );
  }

  const duration = (chunk.end - chunk.start).toFixed(2);

  return (
    <div data-testid="chunk-inspector" style={{ padding: 16 }}>
      <h3 style={{ margin: "0 0 12px", fontSize: 15 }}>Chunk Inspector</h3>
      <table style={{ borderCollapse: "collapse", width: "100%", fontSize: 14 }}>
        <tbody>
          <tr>
            <td style={labelStyle}>Time</td>
            <td data-testid="chunk-time">
              {chunk.start.toFixed(2)}s – {chunk.end.toFixed(2)}s ({duration}s)
            </td>
          </tr>
          <tr>
            <td style={labelStyle}>Tone</td>
            <td data-testid="chunk-tone">{chunk.tone}</td>
          </tr>
          <tr>
            <td style={labelStyle}>Score</td>
            <td data-testid="chunk-score">{chunk.score} / 10</td>
          </tr>
          <tr>
            <td style={labelStyle}>Color</td>
            <td>
              <span
                data-testid="chunk-color-swatch"
                style={{
                  display: "inline-block",
                  width: 14,
                  height: 14,
                  background: chunk.color,
                  border: "1px solid #ccc",
                  verticalAlign: "middle",
                  marginRight: 6,
                  borderRadius: 2,
                }}
              />
              <span data-testid="chunk-color">{chunk.color}</span>
            </td>
          </tr>
          <tr>
            <td style={labelStyle}>Anger</td>
            <td data-testid="chunk-anger">
              {ANGER_EMOJI[chunk.anger_level]} {chunk.anger_level} / 3
            </td>
          </tr>
          <tr>
            <td style={labelStyle}>Frustration</td>
            <td data-testid="chunk-frustration">
              {FRUSTRATION_EMOJI[chunk.frustration_level]} {chunk.frustration_level} / 3
            </td>
          </tr>
          <tr>
            <td style={labelStyle}>Sarcasm</td>
            <td data-testid="chunk-sarcasm">
              {chunk.sarcasm_flag ? "✓ Detected" : "✗ None"}
            </td>
          </tr>
          <tr>
            <td colSpan={2} style={{ paddingTop: 10 }}>
              <p
                data-testid="chunk-text"
                style={{ margin: 0, fontStyle: "italic", color: "#333", lineHeight: 1.5 }}
              >
                "{chunk.text}"
              </p>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}

const labelStyle: React.CSSProperties = {
  fontWeight: 600,
  paddingRight: 12,
  paddingBottom: 6,
  verticalAlign: "top",
  whiteSpace: "nowrap",
  color: "#555",
};
