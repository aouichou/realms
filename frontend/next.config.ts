import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  reactCompiler: true,
  output: "standalone",
  
  // Empty turbopack config to enable Turbopack (default in Next.js 16)
  turbopack: {},
};

export default nextConfig;
