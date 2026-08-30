import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // pdfjs-dist references an optional Node "canvas" module we never use (we
  // only extract PDF text in the browser). Stub it so the build resolves —
  // covering both Turbopack and webpack.
  turbopack: {
    resolveAlias: {
      canvas: "./empty-module.js",
    },
  },
  webpack: (config) => {
    config.resolve = config.resolve || {};
    config.resolve.alias = { ...(config.resolve.alias || {}), canvas: false };
    return config;
  },
  headers: async () => [
    {
      source: "/sw.js",
      headers: [
        { key: "Cache-Control", value: "public, max-age=0, must-revalidate" },
        { key: "Service-Worker-Allowed", value: "/" },
      ],
    },
  ],
};

export default nextConfig;
