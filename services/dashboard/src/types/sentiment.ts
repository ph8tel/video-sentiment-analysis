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

export interface MediaIngestChunk {
  start: number;
  end: number;
  text: string;
  speaker: string;
}

export interface MediaIngestResult {
  chunks: MediaIngestChunk[];
  speaker_order: string[];
  meta: Record<string, unknown>;
}

export interface MultiSpeakerTimelines {
  overall: SentimentTimeline;
  speakerLeft: SentimentTimeline | null;
  speakerRight: SentimentTimeline | null;
}

