import type { NextRequest } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

export async function GET(_request: NextRequest, ctx: RouteContext<"/api/chart/[ticker]">) {
  const { ticker } = await ctx.params;

  let res: Response;
  try {
    res = await fetch(`${BACKEND_URL}/chart/${encodeURIComponent(ticker)}`);
  } catch {
    return Response.json({ ticker, prices: [] }, { status: 502 });
  }

  const data = await res.json();
  return Response.json(data, { status: res.status });
}
