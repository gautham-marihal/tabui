import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

type RawBot = {
  id?: unknown;
  name?: unknown;
  deployed?: unknown;
  latest_version?: unknown;
};

type SelectableAgent = {
  id: string;
  name: string;
  ref: string;
  version: string;
};

function corsHeaders(request: NextRequest) {
  const configuredOrigins = (process.env.ALLOWED_ORIGINS_TO_CALL_API || "http://localhost:5174,http://localhost:3000")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
  const requestOrigin = request.headers.get("origin");
  const allowOrigin = requestOrigin && configuredOrigins.includes(requestOrigin)
    ? requestOrigin
    : configuredOrigins[0] || "http://localhost:5174";

  return {
    "Access-Control-Allow-Origin": allowOrigin,
    "Access-Control-Allow-Methods": "GET, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
    Vary: "Origin",
  };
}

function normalizeBots(payload: unknown): SelectableAgent[] {
  const records: unknown[] = Array.isArray(payload)
    ? payload
    : payload && typeof payload === "object" && Array.isArray((payload as { bots?: unknown }).bots)
      ? (payload as { bots: unknown[] }).bots
      : payload && typeof payload === "object" && Array.isArray((payload as { data?: unknown }).data)
        ? (payload as { data: unknown[] }).data
        : [];

  const result: SelectableAgent[] = [];
  for (const record of records) {
    if (!record || typeof record !== "object") continue;
    const bot = record as RawBot;
    if (typeof bot.id !== "string" || !bot.id.trim()) continue;
    const name = typeof bot.name === "string" && bot.name.trim() ? bot.name : bot.id;
    const deployments = bot.deployed && typeof bot.deployed === "object" && !Array.isArray(bot.deployed)
      ? Object.entries(bot.deployed as Record<string, unknown>)
      : [];

    // Only offer versions that are deployed to an environment. Draft-only agents
    // cannot reliably be started through a runtime dispatch.
    for (const [ref, versionValue] of deployments) {
      if (!ref || typeof versionValue !== "string" || !versionValue.trim()) continue;
      result.push({ id: bot.id, name, ref, version: versionValue });
    }
  }

  return result.sort((a, b) => a.name.localeCompare(b.name) || a.ref.localeCompare(b.ref));
}

export async function OPTIONS(request: NextRequest) {
  return new NextResponse(null, { status: 204, headers: corsHeaders(request) });
}

export async function GET(request: NextRequest) {
  const headers = corsHeaders(request);
  const baseUrl = (process.env.WEAVE_API_BASE_URL || "http://localhost:5173").replace(/\/+$/, "");
  let endpoint: URL;
  try {
    // appended, so a base with a path keeps it (Weave Studio's dev server serves its API at http://localhost:5173/api)
    endpoint = new URL(`${baseUrl}/bots`);
  } catch {
    return NextResponse.json(
      { error: "WEAVE_API_BASE_URL is invalid. Set it to the Weave Studio API base URL in showcase/.env.local." },
      { status: 500, headers },
    );
  }

  try {
    const response = await fetch(endpoint, {
      method: "GET",
      headers: { Accept: "application/json" },
      cache: "no-store",
      signal: AbortSignal.timeout(10000),
    });

    const contentType = response.headers.get("content-type") || "";
    const responseText = await response.text();
    let payload: unknown;
    try {
      payload = JSON.parse(responseText);
    } catch {
      const detail = contentType.includes("text/html") || responseText.trimStart().startsWith("<!DOCTYPE")
        ? "The endpoint returned an HTML page, not JSON. The Weave UI URL and the /bots API URL may be different. Update WEAVE_API_BASE_URL in showcase/.env.local to the API server's base URL."
        : "The endpoint did not return valid JSON.";
      return NextResponse.json(
        { error: `${detail} Requested: ${endpoint.toString()}` },
        { status: 502, headers },
      );
    }

    if (!response.ok) {
      return NextResponse.json(
        { error: `Weave Studio GET /bots returned HTTP ${response.status}.`, status: response.status },
        { status: 502, headers },
      );
    }

    const agents = normalizeBots(payload);
    if (agents.length === 0) {
      return NextResponse.json(
        { agents: [], error: "GET /bots responded, but no deployed bot environments were found." },
        { status: 200, headers },
      );
    }

    return NextResponse.json({ agents }, { status: 200, headers });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown Weave Studio API error";
    console.error("[bots API] Failed to fetch Weave Studio agents:", message);
    return NextResponse.json(
      { error: `Could not reach Weave Studio at ${endpoint.toString()}. ${message}` },
      { status: 502, headers },
    );
  }
}
