"use client";

import { useEffect, useState } from "react";
import { StockChart } from "@/components/StockChart";
import type { ChartResponse } from "@/lib/chart";
import { detectTicker } from "@/lib/chart";
import type { Entry } from "@/lib/entry";

export function LedgerEntry({ entry, index }: { entry: Entry; index: number }) {
  const ticker =
    entry.status === "done" && entry.result?.accepted ? detectTicker(entry.result.sql) : null;

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

        {entry.status === "done" && entry.result && (
          <div className="space-y-3">
            <pre className="overflow-x-auto border border-line bg-panel px-4 py-3 font-mono text-[13px] leading-relaxed text-ink">
              {entry.result.sql}
            </pre>

            <div className="flex flex-wrap items-center gap-2 font-sans text-xs">
              {entry.result.accepted ? (
                <span className="border border-navy bg-navy px-2 py-0.5 text-paper">
                  validated · read-only
                </span>
              ) : (
                <span className="border border-blocked px-2 py-0.5 text-blocked">
                  blocked by guardrail
                </span>
              )}
              {entry.result.accepted && (
                <span className="text-muted">
                  {entry.result.row_count} row{entry.result.row_count === 1 ? "" : "s"} ·{" "}
                  {entry.result.elapsed_ms}ms
                </span>
              )}
              {!entry.result.accepted && entry.result.rejection_reason && (
                <span className="text-muted">{entry.result.rejection_reason}</span>
              )}
            </div>

            {entry.result.answer && (
              <p className="font-sans text-[15px] leading-relaxed text-ink">{entry.result.answer}</p>
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
