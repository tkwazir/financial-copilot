export type TickerQuote = {
  ticker: string;
  close: number;
  change: number;
  change_pct: number;
  sparkline: number[];
};

export type TickersResponse = {
  quotes: TickerQuote[];
};
