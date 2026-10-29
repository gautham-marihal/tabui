import { S3Client, ListObjectsV2Command } from "@aws-sdk/client-s3";

import { getEnvVariables } from "../../../lib/get-env-variables";

const excludeRegex = new RegExp(/(?!)/);

export async function GET(request: Request) {
  const url = new URL(request.url);
  const agentId = url.searchParams.get("agentId");
  const prefix: string = url.searchParams.get("prefix") || "";

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
    const client = new S3Client({ region: process.env.AWS_REGION });

    const command = new ListObjectsV2Command({
      Bucket: process.env.AWS_S3_BUCKET_NAME, // Bucket name from environment variable
      Prefix: prefix,
      Delimiter: "/",
    });

    const response = await client.send(command);

    const folders =
      response.CommonPrefixes?.filter(
        ({ Prefix }) => Prefix !== undefined && !excludeRegex.test(Prefix)
      ).map(({ Prefix }) => ({
        name: Prefix !== undefined && Prefix.slice(prefix.length),
        path: Prefix,
        url: `?prefix=${Prefix}`,
      })) || [];

    const objects =
      response.Contents?.filter(
        ({ Key }) => Key !== undefined && !excludeRegex.test(Key)
      ).map(({ Key, LastModified, Size }) => ({
        name: Key !== undefined && Key.slice(prefix.length),
        lastModified: LastModified,
        size: Size,
        path: Key,
        url: `/api/s3/download?key=${Key}`,
      })) || [];

    return Response.json({ folders, objects }, { status: 200, ...corsHeaders });
  } catch (e) {
    return Response.json(
      { error: (e as Error).message },
      { status: 500, ...corsHeaders }
    );
  }
}
