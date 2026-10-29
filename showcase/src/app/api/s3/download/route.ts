import { S3Client, GetObjectCommand } from "@aws-sdk/client-s3";

import { getEnvVariables } from "../../../../lib/get-env-variables";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const agentId = url.searchParams.get("agentId");
  const key: string = url.searchParams.get("key") || "";

  const { allowedOriginsToCallAPI } = getEnvVariables(agentId ?? "");

  const corsHeaders = {
    headers: {
      "Access-Control-Allow-Origin": allowedOriginsToCallAPI || "",
      "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type, Authorization",
    },
  };

  try {
    // Initialize the S3 client with the region from environment variables
    const s3Client = new S3Client({ region: process.env.AWS_REGION });

    const command = new GetObjectCommand({
      Bucket: process.env.AWS_S3_BUCKET_NAME, // Bucket name from environment variable
      Key: key,
    });

    // Get object from S3
    const { Body, ContentType, ContentLength } = await s3Client.send(command);

    if (!Body || !ContentLength) {
      return new Response("Unexpected error: ", {
        status: 404,
        ...corsHeaders,
      });
    }

    // Create headers for the response
    const headers = new Headers({
      "Content-Type": ContentType || "application/octet-stream",
      "Content-Length": ContentLength.toString(),
      "Content-Disposition": `attachment; filename="${key.split("/").pop()}"`,
      ...corsHeaders.headers,
    });

    // Stream the file to the client
    //@ts-expect-error - TODO: Fix later
    return new Response(Body, { headers });
  } catch (err: any) {
    if (err.name === "NoSuchKey") {
      return Response.json(
        { error: "File not found in S3" },
        { status: 404, ...corsHeaders }
      );
    }

    if (err.name === "AccessDenied") {
      return Response.json(
        { error: "Access denied to S3 resource" },
        { status: 403, ...corsHeaders }
      );
    }

    return Response.json(
      { error: (err as Error).message },
      { status: 500, ...corsHeaders }
    );
  }
}
