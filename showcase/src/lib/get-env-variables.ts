export function getEnvVariables(agentId: string | "") {
  // Prefer the three shared LiveKit values entered in showcase/.env.local.
  // Keep per-agent variables as a fallback for older deployments.
  const varPrefix = agentId.toUpperCase().replace(/-/g, "_");

  return {
    livekitURL:
      process.env.LIVEKIT_URL ||
      process.env[`NEXT_PUBLIC_${varPrefix}_LIVEKIT_URL`],
    livekitAPIKey:
      process.env.LIVEKIT_API_KEY ||
      process.env[`LIVEKIT_${varPrefix}_API_KEY`],
    liveKitAPISecret:
      process.env.LIVEKIT_API_SECRET ||
      process.env[`LIVEKIT_${varPrefix}_API_SECRET`],
    allowedOriginsToCallAPI: process.env.ALLOWED_ORIGINS_TO_CALL_API,
    awsRegion: process.env.AWS_REGION,
    awsS3BucketName: process.env.AWS_S3_BUCKET_NAME,
  };
}
