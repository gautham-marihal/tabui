import { NextRequest, NextResponse } from "next/server";

import { bankFetch, crmCorsHeaders, CrmNotConfigured, hasCrmKey } from "@/lib/crm";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

// The bank's CRM for other apps: Weave Studio's Integrations (check, browse) and agents' tools (look up, verify, hand
// over). /api/crm/<path> answers what the bank's /crm/<path> does, for callers that send CRM_API_KEY as
// "Authorization: Bearer <key>". The bank's own address and key stay on this server.

type Context = { params: Promise<{ path: string[] }> };

// a path is plain words, digits and hyphens: nothing that could climb out of /crm
const SAFE_PART = /^[A-Za-z0-9_-]+$/;
const MAX_BODY = 16_000;

export async function OPTIONS(request: NextRequest) {
  return new NextResponse(null, { status: 204, headers: crmCorsHeaders(request) });
}

export async function GET(request: NextRequest, context: Context) {
  return forward(request, context, "GET");
}

export async function POST(request: NextRequest, context: Context) {
  return forward(request, context, "POST");
}

async function forward(request: NextRequest, { params }: Context, method: "GET" | "POST") {
  const headers = crmCorsHeaders(request);
  if (!hasCrmKey(request)) {
    return NextResponse.json({ error: "missing_or_wrong_key" }, { status: 401, headers });
  }
  const { path } = await params;
  if (!path.length || !path.every((part) => SAFE_PART.test(part))) {
    return NextResponse.json({ error: "not_found" }, { status: 404, headers });
  }
  let body: string | undefined;
  if (method === "POST") {
    body = await request.text();
    if (body.length > MAX_BODY) return NextResponse.json({ error: "body_too_large" }, { status: 413, headers });
  }
  try {
    const answer = await bankFetch(path.join("/"), { method, body, search: request.nextUrl.search });
    return NextResponse.json(answer.body, { status: answer.status, headers });
  } catch (error) {
    if (error instanceof CrmNotConfigured) {
      return NextResponse.json({ error: error.message }, { status: 503, headers });
    }
    const message = error instanceof Error ? error.message : "Unknown error";
    console.error("[crm API] The bank did not answer:", message);
    return NextResponse.json({ error: `The bank's CRM did not answer. ${message}` }, { status: 502, headers });
  }
}
