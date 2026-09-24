export type NewsSource = {
  title: string;
  publisher: string;
  url: string;
  pub_date: string;
};

export type QueryResponse = {
  question: string;
  mode: "data" | "news";
  sql: string | null;
  accepted: boolean;
  rejection_reason: string | null;
  answer: string | null;
  row_count: number | null;
  ticker: string | null;
  sources: NewsSource[] | null;
  elapsed_ms: number;
};
