export type PricePoint = { date: string; close: number };

export type ChartResponse = {
  ticker: string;
  prices: PricePoint[];
};

/** Extracts up to `max` distinct tickers referenced in generated SQL —
 * matches both `TICKER = 'AAPL'` and `TICKER IN ('AAPL', 'MSFT')` shapes —
 * so comparison questions ("compare MSFT vs GOOGL") get a chart per ticker,
 * not just single-ticker lookups. Only offered when the query actually
 * touches the market-price tables. */
export function detectTickers(sql: string, max = 4): string[] {
  if (!/FACT_MARKET_PRICES|DIM_TICKERS/i.test(sql)) return [];

  const found = new Set<string>();

  for (const m of sql.matchAll(/\bTICKER\s*=\s*'([A-Za-z.-]+)'/gi)) {
    found.add(m[1].toUpperCase());
  }

  for (const m of sql.matchAll(/\bTICKER\s+IN\s*\(([^)]+)\)/gi)) {
    for (const v of m[1].matchAll(/'([A-Za-z.-]+)'/g)) {
      found.add(v[1].toUpperCase());
    }
  }

  return [...found].slice(0, max);
}
