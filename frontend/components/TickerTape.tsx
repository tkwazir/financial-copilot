"use client";

import { useEffect, useState } from "react";
import type { TickerQuote, TickersResponse } from "@/lib/tickers";

const SPARK_WIDTH = 48;
const SPARK_HEIGHT = 20;

function Sparkline({ values, color }: { values: number[]; color: string }) {
  if (values.length < 2) return null;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const n = values.length;

  const path = values
    .map((v, i) => {
      const x = (i / (n - 1)) * SPARK_WIDTH;
      const y = SPARK_HEIGHT - ((v - min) / range) * SPARK_HEIGHT;
      return `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");

  return (
    <svg width={SPARK_WIDTH} height={SPARK_HEIGHT} viewBox={`0 0 ${SPARK_WIDTH} ${SPARK_HEIGHT}`}>
      <path d={path} fill="none" stroke={color} strokeWidth="1.25" />
    </svg>
  );
}

function QuoteItem({ quote }: { quote: TickerQuote }) {
  const isUp = quote.change >= 0;
  const color = isUp ? "var(--color-gain)" : "var(--color-blocked)";
  return (
    <div className="flex items-center gap-3 border-r border-paper/10 px-5 py-3 whitespace-nowrap">
      <div className="font-mono text-xs">
        <div className="text-paper/90">{quote.ticker}</div>
        <div className="mt-0.5 text-paper/60">${quote.close.toFixed(2)}</div>
      </div>
      <Sparkline values={quote.sparkline} color={color} />
      <div className="font-mono text-xs" style={{ color }}>
        {isUp ? "+" : ""}
        {quote.change_pct.toFixed(2)}%
      </div>
    </div>
  );
}

export function TickerTape() {
  const [quotes, setQuotes] = useState<TickerQuote[]>([]);
  const [reducedMotion, setReducedMotion] = useState(
    () => typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches,
  );

  useEffect(() => {
    let cancelled = false;
    fetch("/api/tickers")
      .then((res) => res.json())
      .then((data: TickersResponse) => {
        if (!cancelled) setQuotes(data.quotes ?? []);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const handler = () => setReducedMotion(mq.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

  if (quotes.length === 0) return null;

  const label = (
    <div className="flex shrink-0 items-center border-r border-paper/15 px-4 py-3 font-sans text-xs whitespace-nowrap text-paper/70">
      Top {quotes.length} gainers today
    </div>
  );

  if (reducedMotion) {
    return (
      <div className="flex bg-navy-deep">
        {label}
        <div className="overflow-x-auto">
          <div className="flex w-max">
            {quotes.map((q) => (
              <QuoteItem key={q.ticker} quote={q} />
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex bg-navy-deep">
      {label}
      <div className="overflow-hidden">
        <div className="flex w-max animate-[ticker-scroll_60s_linear_infinite]">
          {quotes.map((q) => (
            <QuoteItem key={`a-${q.ticker}`} quote={q} />
          ))}
          {quotes.map((q) => (
            <QuoteItem key={`b-${q.ticker}`} quote={q} />
          ))}
        </div>
      </div>
    </div>
  );
}
