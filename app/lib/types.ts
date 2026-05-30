export interface Chunk {
  chunk_index: number;
  text: string;
  start: number;
  end: number;
}

export interface Video {
  video_id: "A" | "B";
  url: string;
  platform: "youtube" | "instagram";
  creator: string | null;
  follower_count: number | null;
  title: string | null;
  upload_date: string | null;
  duration_sec: number | null;
  views: number;
  likes: number;
  comments: number;
  hashtags: string[];
  thumbnail: string | null;
  engagement_rate: number;
  transcript: string;
  transcript_source: "captions" | "whisper" | "manual" | "none";
  chunks: Chunk[];
}

export interface IngestResponse {
  session_id: string;
  video_a: Video;
  video_b: Video;
  chunks_indexed: { A: number; B: number };
}

export interface Source {
  video_id: "A" | "B";
  chunk_index: number;
  start: number;
  end: number;
  text: string;
  score: number | null;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  streaming?: boolean;
}
