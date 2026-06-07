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

export interface IngestRefResponse {
  ingest: string[];
  skipped: string[];
  total_found: number;
}
