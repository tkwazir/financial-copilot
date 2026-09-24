"use client";

import { useCallback, useMemo, useRef, useState } from "react";
import type { PricePoint } from "@/lib/chart";

const PERIODS = [
  { key: "1W", days: 7 },
  { key: "1M", days: 30 },
  { key: "3M", days: 90 },
  { key: "6M", days: 182 },
  { key: "1Y", days: 365 },
  { key: "ALL", days: null },
] as const;

type PeriodKey = (typeof PERIODS)[number]["key"];

const WIDTH = 640;
const HEIGHT = 180;
const PAD_Y = 16;

export function StockChart({ ticker, series }: { ticker: string; series: PricePoint[] }) {
  const [period, setPeriod] = useState<PeriodKey>("3M");
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);

  const sorted = useMemo(() => [...series].sort((a, b) => a.date.localeCompare(b.date)), [series]);

  const filtered = useMemo(() => {
    const def = PERIODS.find((p) => p.key === period);
    if (!def || def.days === null || sorted.length === 0) return sorted;
    const cutoff = new Date(sorted[sorted.length - 1].date);
    cutoff.setDate(cutoff.getDate() - def.days);
    const cutoffStr = cutoff.toISOString().slice(0, 10);
    return sorted.filter((p) => p.date >= cutoffStr);
  }, [sorted, period]);

  const { linePath, areaPath, points } = useMemo(() => {
    if (filtered.length === 0) {
      return { linePath: "", areaPath: "", points: [] as { x: number; y: number }[] };
    }
    const closes = filtered.map((p) => p.close);
    const min = Math.min(...closes);
    const max = Math.max(...closes);
    const range = max - min || 1;
    const n = filtered.length;

    const pts = filtered.map((p, i) => ({
      x: n === 1 ? WIDTH : (i / (n - 1)) * WIDTH,
      y: PAD_Y + (HEIGHT - PAD_Y * 2) * (1 - (p.close - min) / range),
    }));

    const linePath = pts.map((pt, i) => `${i === 0 ? "M" : "L"}${pt.x.toFixed(1)},${pt.y.toFixed(1)}`).join(" ");
    const areaPath = `${linePath} L${pts[pts.length - 1].x.toFixed(1)},${HEIGHT} L${pts[0].x.toFixed(1)},${HEIGHT} Z`;

    return { linePath, areaPath, points: pts };
  }, [filtered]);

  const handleMove = useCallback(
    (clientX: number) => {
      const svg = svgRef.current;
      if (!svg || points.length === 0) return;
      const rect = svg.getBoundingClientRect();
      const relX = ((clientX - rect.left) / rect.width) * WIDTH;
      let nearest = 0;
      let best = Infinity;
      points.forEach((pt, i) => {
        const d = Math.abs(pt.x - relX);
        if (d < best) {
          best = d;
          nearest = i;
        }
      });
      setHoverIndex(nearest);
    },
    [points],
  );

  if (filtered.length === 0) return null;

  const first = filtered[0];
  const last = filtered[filtered.length - 1];
  const change = last.close - first.close;
  const changePct = first.close !== 0 ? (change / first.close) * 100 : 0;
  const isUp = change >= 0;
  const lineColor = isUp ? "var(--color-gain)" : "var(--color-blocked)";

  const hovered = hoverIndex !== null ? filtered[hoverIndex] : null;
  const hoveredPoint = hoverIndex !== null ? points[hoverIndex] : null;
  const displayed = hovered ?? last;

  return (
    <div className="border border-line">
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 border-b border-line bg-panel px-4 py-3">
        <div>
          <span className="font-mono text-sm text-muted">{ticker}</span>
          <span className="ml-3 font-serif text-xl text-ink">${displayed.close.toFixed(2)}</span>
        </div>
        <div className="font-sans text-xs" style={{ color: lineColor }}>
          {isUp ? "+" : ""}
          {change.toFixed(2)} ({isUp ? "+" : ""}
          {changePct.toFixed(2)}%) over {period.toLowerCase()}
        </div>
      </div>

      <div className="px-4 py-3">
        <svg
          ref={svgRef}
          viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
          className="w-full touch-none select-none"
          onMouseMove={(e) => handleMove(e.clientX)}
          onMouseLeave={() => setHoverIndex(null)}
          onTouchMove={(e) => handleMove(e.touches[0].clientX)}
          onTouchEnd={() => setHoverIndex(null)}
        >
          <defs>
            <linearGradient id={`area-${ticker}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={lineColor} stopOpacity="0.18" />
              <stop offset="100%" stopColor={lineColor} stopOpacity="0" />
            </linearGradient>
          </defs>
          <path d={areaPath} fill={`url(#area-${ticker})`} stroke="none" />
          <path d={linePath} fill="none" stroke={lineColor} strokeWidth="1.5" />
          {hoveredPoint && (
            <line
              x1={hoveredPoint.x}
              y1={0}
              x2={hoveredPoint.x}
              y2={HEIGHT}
              stroke="var(--color-line)"
              strokeWidth="1"
              strokeDasharray="3,3"
            />
          )}
          <circle
            cx={(hoveredPoint ?? points[points.length - 1]).x}
            cy={(hoveredPoint ?? points[points.length - 1]).y}
            r="2.5"
            fill={lineColor}
          />
        </svg>
        <div className="mt-1 h-4 font-sans text-xs text-muted">{hovered?.date ?? " "}</div>
      </div>

      <div className="flex flex-wrap gap-1 border-t border-line px-4 py-2">
        {PERIODS.map((p) => (
          <button
            key={p.key}
            type="button"
            onClick={() => setPeriod(p.key)}
            className={`border px-2 py-1 font-sans text-xs transition-colors ${
              period === p.key
                ? "border-navy bg-navy text-paper"
                : "border-line text-muted hover:border-navy hover:text-ink"
            }`}
          >
            {p.key}
          </button>
        ))}
      </div>
    </div>
  );
}
