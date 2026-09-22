export type QueryResponse = {
  question: string;
  sql: string;
  accepted: boolean;
  rejection_reason: string | null;
  answer: string | null;
  row_count: number | null;
  elapsed_ms: number;
};
