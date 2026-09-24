"use client";

import { useEffect, useState } from "react";
import { StockChart } from "@/components/StockChart";
import type { ChartResponse } from "@/lib/chart";
import { detectTicker } from "@/lib/chart";
import type { Entry } from "@/lib/entry";

export function LedgerEntry({ entry, index }: { entry: Entry; index: number }) {
  const result = entry.status === "done" ? entry.result : undefined;

  const ticker =
    result?.accepted && result.mode === "news"
      ? result.ticker
      : result?.accepted && result.sql
        ? detectTicker(result.sql)
        : null;

  const [chart, setChart] = useState<ChartResponse | null>(null);

  useEffect(() => {
    if (!ticker) return;
    let cancelled = false;
    fetch(`/api/chart/${ticker}`)
      .then((res) => res.json())
      .then((data: ChartResponse) => {
        if (!cancelled) setChart(data);
      })
      .catch(() => {
        if (!cancelled) setChart(null);
      });
    return () => {
      cancelled = true;
    };
  }, [ticker]);

  return (
    <article className="border border-line bg-paper">
      <div className="flex items-baseline justify-between gap-4 border-b border-line bg-panel px-5 py-3">
        <p className="font-serif text-[17px] leading-snug text-ink">{entry.question}</p>
        <span className="shrink-0 font-sans text-xs tabular-nums text-muted">
          {String(index + 1).padStart(2, "0")}
        </span>
      </div>

      <div className="px-5 py-4">
        {entry.status === "pending" && (
          <p className="font-sans text-sm text-muted">running…</p>
        )}

        {entry.status === "error" && (
          <p className="font-sans text-sm text-blocked">{entry.errorMessage}</p>
        )}

        {result && (
          <div className="space-y-3">
            {result.mode === "news" ? (
              <span className="inline-block border border-navy bg-navy px-2 py-0.5 font-sans text-xs text-paper">
                sourced from live news
              </span>
            ) : (
              <>
                <pre className="overflow-x-auto border border-line bg-panel px-4 py-3 font-mono text-[13px] leading-relaxed text-ink">
                  {result.sql}
                </pre>

                <div className="flex flex-wrap items-center gap-2 font-sans text-xs">
                  {result.accepted ? (
                    <span className="border border-navy bg-navy px-2 py-0.5 text-paper">
                      validated · read-only
                    </span>
                  ) : (
                    <span className="border border-blocked px-2 py-0.5 text-blocked">
                      blocked by guardrail
                    </span>
                  )}
                  {result.accepted && (
                    <span className="text-muted">
                      {result.row_count} row{result.row_count === 1 ? "" : "s"} · {result.elapsed_ms}ms
                    </span>
                  )}
                  {!result.accepted && result.rejection_reason && (
                    <span className="text-muted">{result.rejection_reason}</span>
                  )}
                </div>
              </>
            )}

            {result.answer && (
              <p className="font-sans text-[15px] leading-relaxed text-ink">{result.answer}</p>
            )}

            {result.mode === "news" && result.sources && result.sources.length > 0 && (
              <ul className="space-y-1.5 border-t border-line pt-3">
                {result.sources.map((s) => (
                  <li key={s.url} className="font-sans text-xs">
                    <a
                      href={s.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-ink underline decoration-line underline-offset-2 hover:text-navy"
                    >
                      {s.title}
                    </a>
                    <span className="text-muted"> — {s.publisher}</span>
                  </li>
                ))}
              </ul>
            )}

            {ticker && chart && chart.prices.length > 0 && (
              <StockChart ticker={chart.ticker} series={chart.prices} />
            )}
          </div>
        )}
      </div>
    </article>
  );
}
