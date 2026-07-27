import type { NextConfig } from "next";

const isGitHubPages = process.env.GITHUB_PAGES === "true";

const nextConfig: NextConfig = {
  ...(isGitHubPages
    ? {
        output: "export",
        basePath: "/openhands-agent-research-lab",
        images: { unoptimized: true },
      }
    : {}),
};

export default nextConfig;
