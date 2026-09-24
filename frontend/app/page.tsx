"use client";

import { useEffect, useRef, useState } from "react";
import { LedgerEntry } from "@/components/LedgerEntry";
import { TickerTape } from "@/components/TickerTape";
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
      <TickerTape />
      <header className="border-b border-line bg-paper">
        <div className="mx-auto flex max-w-[880px] items-baseline justify-between px-6 py-5">
          <div>
            <div className="font-serif text-lg text-ink">Financial Copilot</div>
            <div className="mt-1.5 h-px w-10 bg-navy" />
          </div>
          <span className="font-sans text-xs text-muted">Snowflake · Claude</span>
        </div>
      </header>

      <section className="on-navy bg-navy text-paper">
        <div className="mx-auto max-w-[880px] px-6 py-14">
          <p className="max-w-[42ch] font-serif text-[26px] leading-snug">
            Ask about market prices or transaction activity in plain English. Every answer traces
            back to the exact SQL that ran against a read-only Snowflake warehouse.
          </p>

          <form
            onSubmit={(e) => {
              e.preventDefault();
              ask(input);
            }}
            className="mt-8 flex items-center gap-3 border border-paper/25 bg-navy-deep px-4 py-3 transition-colors focus-within:border-paper/60"
          >
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="What was the average close price for AAPL?"
              className="flex-1 bg-transparent font-sans text-[15px] text-paper placeholder:text-paper/50 focus:outline-none"
              aria-label="Ask a question about market or transaction data"
            />
            <button
              type="submit"
              disabled={pending || !input.trim()}
              className="font-sans text-sm text-paper/70 transition-colors hover:text-paper disabled:cursor-not-allowed disabled:opacity-40"
            >
              {pending ? "asking…" : "ask"}
            </button>
          </form>

          {entries.length === 0 && (
            <div className="mt-4 flex flex-wrap gap-2">
              {EXAMPLES.map((q) => (
                <button
                  key={q}
                  type="button"
                  onClick={() => setInput(q)}
                  className="border border-paper/25 px-2.5 py-1.5 font-sans text-xs text-paper/70 transition-colors hover:border-paper/60 hover:text-paper"
                >
                  {q}
                </button>
              ))}
            </div>
          )}
        </div>
      </section>

      <main className="mx-auto w-full max-w-[880px] flex-1 px-6 py-8">
        <div className="space-y-3">
          {entries.map((entry, i) => (
            <LedgerEntry key={entry.id} entry={entry} index={i} />
          ))}
          <div ref={bottomRef} />
        </div>
      </main>
    </div>
  );
}
