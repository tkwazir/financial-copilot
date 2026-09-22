"use client";

import { useEffect, useRef, useState } from "react";
import { LedgerEntry } from "@/components/LedgerEntry";
import type { Entry } from "@/lib/entry";
import type { QueryResponse } from "@/lib/types";

const EXAMPLES = [
  "What sector is the ticker AMZN in?",
  "How many transactions are flagged as anomalous?",
  "Which merchant category has the highest total transaction amount?",
];

export default function Home() {
  const [entries, setEntries] = useState<Entry[]>([]);
  const [input, setInput] = useState("");
  const [pending, setPending] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [entries]);

  async function ask(question: string) {
    const trimmed = question.trim();
    if (!trimmed || pending) return;

    const id = crypto.randomUUID();
    setEntries((prev) => [...prev, { id, question: trimmed, status: "pending" }]);
    setInput("");
    setPending(true);

    try {
      const res = await fetch("/api/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: trimmed }),
      });

      if (!res.ok && res.status === 502) {
        const body = await res.json();
        setEntries((prev) =>
          prev.map((e) => (e.id === id ? { ...e, status: "error", errorMessage: body.error } : e)),
        );
        return;
      }

      const data: QueryResponse = await res.json();
      setEntries((prev) => prev.map((e) => (e.id === id ? { ...e, status: "done", result: data } : e)));
    } catch {
      setEntries((prev) =>
        prev.map((e) =>
          e.id === id
            ? { ...e, status: "error", errorMessage: "Something went wrong asking that question." }
            : e,
        ),
      );
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="flex min-h-screen flex-col">
      <header className="border-b border-line">
        <div className="mx-auto max-w-[760px] px-6 py-10">
          <h1 className="text-2xl font-medium text-paper">Financial Copilot</h1>
          <p className="mt-2 max-w-[60ch] text-muted">
            Ask about market prices or transaction activity in plain English. Every answer traces
            back to the exact SQL that ran against a read-only Snowflake warehouse.
          </p>
        </div>
      </header>

      <main className="mx-auto w-full max-w-[760px] flex-1 px-6 py-8">
        {entries.length === 0 && (
          <div className="mb-8 flex flex-wrap gap-2">
            {EXAMPLES.map((q) => (
              <button
                key={q}
                type="button"
                onClick={() => setInput(q)}
                className="rounded border border-line px-2.5 py-1.5 font-mono text-xs text-muted transition-colors hover:border-brass hover:text-paper"
              >
                {q}
              </button>
            ))}
          </div>
        )}

        <div>
          {entries.map((entry, i) => (
            <LedgerEntry key={entry.id} entry={entry} index={i} />
          ))}
          <div ref={bottomRef} />
        </div>
      </main>

      <div className="sticky bottom-0 border-t border-line bg-ink/95 backdrop-blur">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            ask(input);
          }}
          className="mx-auto flex max-w-[760px] items-center gap-3 px-6 py-4"
        >
          <span className="select-none font-mono text-brass" aria-hidden>
            &gt;
          </span>
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="What was the average close price for AAPL?"
            className="flex-1 bg-transparent text-[15px] text-paper placeholder:text-muted focus:outline-none"
            aria-label="Ask a question about market or transaction data"
          />
          <button
            type="submit"
            disabled={pending || !input.trim()}
            className="font-mono text-sm text-muted transition-colors hover:text-paper disabled:cursor-not-allowed disabled:opacity-40"
          >
            {pending ? "asking…" : "ask"}
          </button>
        </form>
      </div>
    </div>
  );
}
