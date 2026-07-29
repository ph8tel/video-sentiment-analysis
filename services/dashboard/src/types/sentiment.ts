export type Tone =
  | "VERY_NEGATIVE"
  | "NEGATIVE"
  | "SLIGHTLY_NEGATIVE"
  | "NEUTRAL"
  | "SLIGHTLY_POSITIVE"
  | "POSITIVE"
  | "VERY_POSITIVE";

export interface ScoredChunk {
  start: number;
  end: number;
  tone: Tone;
  score: number;
  color: string;
  text: string;
  anger_level: number;       // 0–3: 😐 😠 😡 💥
  frustration_level: number; // 0–3: 😐 😤 😣 🤬
  sarcasm_flag: boolean;
}

export interface OverallScore {
  score: number;
  tone: Tone;
}

export interface SentimentTimeline {
  chunks: ScoredChunk[];
  overall: OverallScore;
}
