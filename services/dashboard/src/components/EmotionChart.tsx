import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Legend,
} from "recharts";
import { ScoredChunk } from "../types/sentiment";

interface Props {
  chunks: ScoredChunk[];
}

export function EmotionChart({ chunks }: Props) {
  const data = chunks.map((chunk) => ({
    time: `${chunk.start.toFixed(1)}s`,
    anger: chunk.anger_level,
    frustration: chunk.frustration_level,
  }));

  return (
    <div data-testid="emotion-chart">
      <h3 style={{ margin: "0 0 8px", fontSize: 15 }}>Anger & Frustration Trend</h3>
      <ResponsiveContainer width="100%" height={180}>
        <LineChart data={data} margin={{ top: 4, right: 48, bottom: 4, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="time" tick={{ fontSize: 11 }} />
          <YAxis
            domain={[0, 3]}
            ticks={[0, 1, 2, 3]}
            tick={{ fontSize: 11 }}
          />
          <Tooltip />
          <Legend />
          <Line
            type="monotone"
            dataKey="anger"
            stroke="#e53935"
            dot
            name="Anger 😠 (0–3)"
            strokeWidth={2}
          />
          <Line
            type="monotone"
            dataKey="frustration"
            stroke="#fb8c00"
            dot
            name="Frustration 😤 (0–3)"
            strokeWidth={2}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
