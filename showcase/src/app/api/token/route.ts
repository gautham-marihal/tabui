import { NextRequest, NextResponse } from "next/server";
import type { AccessTokenOptions, VideoGrant } from "livekit-server-sdk";
import { AccessToken, AgentDispatchClient } from "livekit-server-sdk";

import { generateRandomAlphanumeric } from "../../../lib/util";
import type { TokenResult } from "../../../lib/types";
import { getEnvVariables } from "../../../lib/get-env-variables";

export const dynamic = "force-dynamic";

const createToken = (
  userInfo: AccessTokenOptions,
  grant: VideoGrant,
  livekitAPIKey: string,
  liveKitAPISecret: string,
) => {
  const token = new AccessToken(livekitAPIKey, liveKitAPISecret, userInfo);
  token.addGrant(grant);
  return token.toJwt();
};

function corsHeaders(request: NextRequest) {
  const allowedOrigins = (process.env.ALLOWED_ORIGINS_TO_CALL_API || "http://localhost:5174,http://localhost:3000")
    .split(",")
    .map((value) => value.trim())
    .filter(Boolean);
  const origin = request.headers.get("origin");
  const allowOrigin = origin && allowedOrigins.includes(origin)
    ? origin
    : allowedOrigins[0] || "http://localhost:5174";
  return {
    "Access-Control-Allow-Origin": allowOrigin,
    "Access-Control-Allow-Methods": "GET, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
    Vary: "Origin",
  };
}

export async function OPTIONS(request: NextRequest) {
  return new NextResponse(null, { status: 204, headers: corsHeaders(request) });
}

export async function GET(request: NextRequest) {
  const url = new URL(request.url);
  const botId = (url.searchParams.get("botId") || url.searchParams.get("agentId") || process.env.LIVEKIT_BOT_ID || "nimbus-care").trim();
  const botRef = (url.searchParams.get("ref") || process.env.LIVEKIT_BOT_REF || "development").trim();
  const { livekitURL, livekitAPIKey, liveKitAPISecret } = getEnvVariables(botId);
  const headers = corsHeaders(request);

  if (!livekitURL || !livekitAPIKey || !liveKitAPISecret) {
    return NextResponse.json(
      { error: "LiveKit configuration is missing. Set LIVEKIT_URL, LIVEKIT_API_KEY, and LIVEKIT_API_SECRET in showcase/.env.local." },
      { status: 500, headers },
    );
  }
  if (!/^wss?:\/\//i.test(livekitURL)) {
    return NextResponse.json(
      { error: "LIVEKIT_URL must start with wss:// (or ws:// for local development)." },
      { status: 500, headers },
    );
  }
  if (!botId || !botRef) {
    return NextResponse.json(
      { error: "A bot id and deployment reference are required." },
      { status: 400, headers },
    );
  }

  try {
    const roomName = `tab-${generateRandomAlphanumeric(4)}-${generateRandomAlphanumeric(4)}`;
    const identity = `user-${generateRandomAlphanumeric(4)}`;
    const grant: VideoGrant = {
      room: roomName,
      roomJoin: true,
      canPublish: true,
      canPublishData: true,
      canSubscribe: true,
      canUpdateOwnMetadata: true,
    };

    const token = await createToken({ identity }, grant, livekitAPIKey, liveKitAPISecret);
    const agentName = process.env.LIVEKIT_AGENT_NAME || "agent-builder-runtime";
    const dispatchHost = livekitURL.replace(/^wss:/i, "https:").replace(/^ws:/i, "http:");
    const dispatchClient = new AgentDispatchClient(dispatchHost, livekitAPIKey, liveKitAPISecret);

    await dispatchClient.createDispatch(roomName, agentName, {
      metadata: JSON.stringify({ bot: botId, ref: botRef }),
    });

    const result: TokenResult & { livekitURL: string; roomName: string; botId: string; ref: string } = {
      identity,
      accessToken: token,
      livekitURL,
      roomName,
      botId,
      ref: botRef,
    };
    return NextResponse.json(result, { status: 200, headers });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown token/dispatch error";
    console.error("[token API] Failed to create token or dispatch agent:", message);
    return NextResponse.json({ error: message }, { status: 500, headers });
  }
}
