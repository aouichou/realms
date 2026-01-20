import type { NextConfig } from "next";

const nextConfig: NextConfig = {
	/* config options here */
	reactCompiler: true,
	output: "standalone",

	// Empty turbopack config to enable Turbopack (default in Next.js 16)
	turbopack: {},

	images: {
		unoptimized: true, // Disable image optimization for localhost development
		domains: ['localhost'],
		remotePatterns: [
			{
				protocol: 'http',
				hostname: 'localhost',
				port: '8000',
				pathname: '/media/**',
			},
			{
				protocol: 'http',
				hostname: 'localhost',
				pathname: '/media/**',
			},
		],
	},
};

export default nextConfig;
