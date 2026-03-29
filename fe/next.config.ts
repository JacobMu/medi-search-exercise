import type { NextConfig } from "next";

const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";

const nextConfig: NextConfig = {
	async rewrites() {
		return [
			{
				source: "/api/:path*",
				destination: `${backendUrl}/:path*`,
			},
			{
				source: "/output/:path*",
				destination: `${backendUrl}/output/:path*`,
			},
		];
	},
};

export default nextConfig;
