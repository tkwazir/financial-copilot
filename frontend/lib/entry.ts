import type { QueryResponse } from "./types";

export type Entry = {
  id: string;
  question: string;
  status: "pending" | "done" | "error";
  result?: QueryResponse;
  errorMessage?: string;
};
