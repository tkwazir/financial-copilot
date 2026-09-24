const BACKEND_URL = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

export async function GET() {
  let res: Response;
  try {
    res = await fetch(`${BACKEND_URL}/tickers`);
  } catch {
    return Response.json({ quotes: [] }, { status: 502 });
  }

  const data = await res.json();
  return Response.json(data, { status: res.status });
}
