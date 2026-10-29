import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Lean, self-contained build for Docker (.next/standalone) - see Dockerfile.
  output: "standalone",
};

export default nextConfig;
