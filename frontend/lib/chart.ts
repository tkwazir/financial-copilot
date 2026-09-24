export type PricePoint = { date: string; close: number };

export type ChartResponse = {
  ticker: string;
  prices: PricePoint[];
};

/** Extracts a ticker from generated SQL, e.g. `WHERE TICKER = 'AAPL'` — only
 * offered as a chart when exactly one ticker is referenced and the query
 * actually touches the market-price tables. */
export function detectTicker(sql: string): string | null {
  if (!/FACT_MARKET_PRICES|DIM_TICKERS/i.test(sql)) return null;
  const matches = [...sql.matchAll(/\bTICKER\s*=\s*'([A-Za-z.]+)'/gi)].map((m) => m[1].toUpperCase());
  const unique = [...new Set(matches)];
  return unique.length === 1 ? unique[0] : null;
}
