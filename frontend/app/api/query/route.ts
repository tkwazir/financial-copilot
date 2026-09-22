import type { NextRequest } from "next/server";

// Kept server-side (not NEXT_PUBLIC_) so the backend address never ships to
// the client bundle. Falls back to local dev default.
const BACKEND_URL = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

export async function POST(request: NextRequest) {
  const body = await request.json();

  let res: Response;
  try {
    res = await fetch(`${BACKEND_URL}/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch {
    return Response.json(
      { error: `Couldn't reach the backend at ${BACKEND_URL}. Is it running?` },
      { status: 502 },
    );
  }

  const data = await res.json();
  return Response.json(data, { status: res.status });
}
