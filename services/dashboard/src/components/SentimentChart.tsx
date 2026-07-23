import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
  CartesianGrid,
  Legend,
} from "recharts";
import { ScoredChunk, OverallScore } from "../types/sentiment";
import { rollingAverage } from "../utils/rollingAverage";

interface Props {
  chunks: ScoredChunk[];
  overall: OverallScore;
}

export function SentimentChart({ chunks, overall }: Props) {
  const scores = chunks.map((c) => c.score);
  const rolling = rollingAverage(scores, 3);

  const data = chunks.map((chunk, i) => ({
    time: `${chunk.start.toFixed(1)}s`,
    score: chunk.score,
    rolling: rolling[i],
  }));

  return (
    <div data-testid="sentiment-chart">
      <h3 style={{ margin: "0 0 8px", fontSize: 15 }}>Sentiment Trend</h3>
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={data} margin={{ top: 4, right: 48, bottom: 4, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="time" tick={{ fontSize: 11 }} />
          <YAxis
            domain={[0, 10]}
            ticks={[0, 2, 3, 5, 6, 8, 10]}
            tick={{ fontSize: 11 }}
          />
          <Tooltip />
          <Legend />
          <ReferenceLine
            y={overall.score}
            stroke="#888"
            strokeDasharray="4 4"
            label={{
              value: `Overall: ${overall.score}`,
              position: "right",
              fontSize: 11,
              fill: "#666",
            }}
          />
          <Line
            type="monotone"
            dataKey="score"
            stroke="#8884d8"
            dot
            name="Score"
          />
          <Line
            type="monotone"
            dataKey="rolling"
            stroke="#82ca9d"
            dot={false}
            name="Rolling avg (3)"
            strokeWidth={2}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
