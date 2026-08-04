import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Cell,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import type { CSSProperties } from "react";
import { ScoredChunk } from "../types/sentiment";

interface Props {
  chunks: ScoredChunk[];
  selectedChunk: ScoredChunk | null;
  onChunkClick: (chunk: ScoredChunk) => void;
  title?: string;
}

interface ChartDatum {
  label: string;
  score: number;
  color: string;
  chunk: ScoredChunk;
}

export function ChunkTimeline({ chunks, selectedChunk, onChunkClick, title = "Chunk Sentiment" }: Props) {
  const data: ChartDatum[] = chunks.map((chunk) => ({
    label: `${chunk.start.toFixed(1)}s`,
    score: chunk.score,
    color: chunk.color,
    chunk,
  }));

  // Recharts renders to SVG/canvas, which isn't reliably clickable via testing-library
  // or a screen reader — expose a hidden, keyboard/test-accessible button per chunk.
  const visuallyHidden: CSSProperties = {
    position: "absolute",
    width: 1,
    height: 1,
    padding: 0,
    margin: -1,
    overflow: "hidden",
    clip: "rect(0, 0, 0, 0)",
    whiteSpace: "nowrap",
    border: 0,
  };

  // Keep the default testid stable for existing single-timeline usage; give
  // additional (e.g. per-speaker) instances a unique testid so several can
  // coexist on screen at once.
  const testId =
    title === "Chunk Sentiment" ? "chunk-timeline" : `chunk-timeline-${title.toLowerCase().replace(/\s+/g, "-")}`;

  return (
    <div data-testid={testId}>
      <h3 style={{ margin: "0 0 8px", fontSize: 15 }}>{title}</h3>
      <div style={visuallyHidden}>
        {chunks.map((chunk, index) => (
          <button
            key={index}
            type="button"
            data-testid={`${testId}-chunk-button-${index}`}
            onClick={() => onChunkClick(chunk)}
          >
            {`Chunk ${index}: ${chunk.start.toFixed(1)}s`}
          </button>
        ))}
      </div>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data} margin={{ top: 4, right: 8, bottom: 4, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="label" tick={{ fontSize: 11 }} />
          <YAxis
            domain={[0, 10]}
            ticks={[0, 2, 3, 5, 6, 8, 10]}
            tick={{ fontSize: 11 }}
          />
          <Tooltip
            formatter={(value: number) => [value, "Score"]}
            labelFormatter={(label) => `Time: ${label}`}
          />
          <Bar
            dataKey="score"
            onClick={(datum: ChartDatum) => onChunkClick(datum.chunk)}
            cursor="pointer"
          >
            {data.map((entry, index) => (
              <Cell
                key={index}
                fill={entry.color}
                stroke={selectedChunk === entry.chunk ? "#000" : "none"}
                strokeWidth={selectedChunk === entry.chunk ? 2 : 0}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
