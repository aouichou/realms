import type { NextConfig } from "next";

const nextConfig: NextConfig = {
	/* config options here */
	reactCompiler: true,
	output: "standalone",

	// Empty turbopack config to enable Turbopack (default in Next.js 16)
	turbopack: {},

	images: {
		unoptimized: true,
		remotePatterns: [
			{
				protocol: 'http',
				hostname: 'localhost',
				port: '8000',
				pathname: '/media/**',
			},
			{
				protocol: 'https',
				hostname: 'images.realms.anguelz.tech',
				pathname: '/**',
			},
			{
				protocol: 'https',
				hostname: 'pub-realms-images.r2.dev',
				pathname: '/**',
			},
			{
				protocol: 'https',
				hostname: 'api.realms.anguelz.tech',
				pathname: '/media/**',
			},
		],
	},
};

export default nextConfig;
