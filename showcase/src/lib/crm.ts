import { timingSafeEqual } from "node:crypto";
import type { NextRequest } from "next/server";

// The bank's CRM, as the showcase reaches it: on the server only, never from the browser. Everything comes from
// showcase/.env.local:
//   BANK_API_URL         where the bank API runs (bank/, e.g. http://localhost:4310)
//   BANK_API_KEY         the key the bank's CRM asks for (the same value as in bank/.env)
//   CRM_API_KEY          the key other apps (Weave Studio's Integrations, agents' tools) send to /api/crm
//   CRM_ALLOWED_ORIGINS  the sites allowed to call /api/crm from a browser, comma-separated

export type BankAnswer = { status: number; body: unknown };

export class CrmNotConfigured extends Error {}

function bankSettings() {
  const url = (process.env.BANK_API_URL || "").trim().replace(/\/+$/, "");
  const key = (process.env.BANK_API_KEY || "").trim();
  if (!url || !key) {
    throw new CrmNotConfigured("The CRM is not set up: add BANK_API_URL and BANK_API_KEY to showcase/.env.local.");
  }
  return { url, key };
}

/** Calls the bank's CRM (a path under /crm) with the bank's key, and returns its status and JSON body. */
export async function bankFetch(path: string, init: { method?: string; body?: string; search?: string } = {}): Promise<BankAnswer> {
  const { url, key } = bankSettings();
  const response = await fetch(`${url}/crm/${path.replace(/^\/+/, "")}${init.search || ""}`, {
    method: init.method || "GET",
    headers: { Accept: "application/json", "Content-Type": "application/json", Authorization: `Bearer ${key}` },
    body: init.body,
    cache: "no-store",
    signal: AbortSignal.timeout(10000),
  });
  const text = await response.text();
  try {
    return { status: response.status, body: text ? JSON.parse(text) : {} };
  } catch {
    return { status: 502, body: { error: "The bank answered with something that is not JSON." } };
  }
}

/** The CORS headers for a browser call to /api/crm: only the configured sites get an answer they can read. */
export function crmCorsHeaders(request: NextRequest): Record<string, string> {
  const allowed = (process.env.CRM_ALLOWED_ORIGINS || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
  const origin = request.headers.get("origin") || "";
  return {
    ...(origin && allowed.includes(origin) ? { "Access-Control-Allow-Origin": origin } : {}),
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
    "Access-Control-Max-Age": "600",
    Vary: "Origin",
  };
}

/** Whether a request carries the CRM key (compared in constant time). Without a key set, nobody is let in. */
export function hasCrmKey(request: NextRequest): boolean {
  const expected = (process.env.CRM_API_KEY || "").trim();
  const given = (request.headers.get("authorization") || "").replace(/^Bearer\s+/i, "").trim();
  if (!expected || !given) return false;
  const a = Buffer.from(given);
  const b = Buffer.from(expected);
  return a.length === b.length && timingSafeEqual(a, b);
}
