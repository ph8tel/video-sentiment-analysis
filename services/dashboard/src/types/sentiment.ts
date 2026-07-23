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
}

export interface OverallScore {
  score: number;
  tone: Tone;
}

export interface SentimentTimeline {
  chunks: ScoredChunk[];
  overall: OverallScore;
}
