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
import { ScoredChunk } from "../types/sentiment";

interface Props {
  chunks: ScoredChunk[];
  selectedChunk: ScoredChunk | null;
  onChunkClick: (chunk: ScoredChunk) => void;
}

interface ChartDatum {
  label: string;
  score: number;
  color: string;
  chunk: ScoredChunk;
}

export function ChunkTimeline({ chunks, selectedChunk, onChunkClick }: Props) {
  const data: ChartDatum[] = chunks.map((chunk) => ({
    label: `${chunk.start.toFixed(1)}s`,
    score: chunk.score,
    color: chunk.color,
    chunk,
  }));

  return (
    <div data-testid="chunk-timeline">
      <h3 style={{ margin: "0 0 8px", fontSize: 15 }}>Chunk Sentiment</h3>
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
