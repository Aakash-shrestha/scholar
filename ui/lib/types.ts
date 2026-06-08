export interface Paper {
  arxiv_id: string;
  title: string;
  short_citation: string;
  abstract: string;
  year: number;
  ingested_at: string;
}

export interface AskResponse {
  question: string;
  answer: string;
  question_type: string;
  retrieved_arxiv_ids: string[];
  latency: number;
}

export interface GraphNode {
  id: string;
  title: string;
  year: number;
  short_citation: string;
}

export interface GraphEdge {
  source: string;
  target: string;
}

export interface GraphResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface IngestRefResponse {
  ingest: string[];
  skipped: string[];
  total_found: number;
}

export type StreamTokenEvent = {
  type: "token";
  token: string;
};

export type StreamDoneEvent = {
  type: "done";
  question_type: string;
  retrieved_arxiv_ids: string[];
  latency: number;
};

export type StreamEvent = StreamTokenEvent | StreamDoneEvent;
