import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

// Create the next-intl plugin
const withNextIntl = createNextIntlPlugin("./i18n/request.ts");

const nextConfig: NextConfig = {
	output: "standalone",
	async rewrites() {
		// Server-side proxy: browser calls /api/proxy/* over HTTPS, Next.js server
		// forwards to the backend over HTTP (no mixed-content restriction server-side).
		// On Vercel set FASTAPI_BACKEND_URL=http://<ip>:8000 (private) and
		// NEXT_PUBLIC_FASTAPI_BACKEND_URL=/api/proxy (public, embedded in JS bundle).
		const backendUrl =
			process.env.FASTAPI_BACKEND_URL ||
			process.env.NEXT_PUBLIC_FASTAPI_BACKEND_URL ||
			"http://localhost:8000";
		return [
			{
				source: "/api/proxy/:path*",
				destination: `${backendUrl}/:path*`,
			},
		];
	},
	reactStrictMode: false,
	typescript: {
		ignoreBuildErrors: true,
	},
	images: {
		remotePatterns: [
			{
				protocol: "https",
				hostname: "**",
			},
		],
	},
	experimental: {
		optimizePackageImports: [
			"lucide-react",
			"recharts",
			"date-fns",
			"@radix-ui/react-icons",
			"@radix-ui/react-avatar",
			"@radix-ui/react-dialog",
			"@radix-ui/react-dropdown-menu",
			"@radix-ui/react-popover",
			"@radix-ui/react-select",
			"@radix-ui/react-tabs",
			"@radix-ui/react-tooltip",
			"@tabler/icons-react",
			"framer-motion",
		],
	},
	// Turbopack config (used during `next dev --turbopack`)
	turbopack: {
		rules: {
			"*.svg": {
				loaders: ["@svgr/webpack"],
				as: "*.js",
			},
		},
	},

	// Configure webpack (SVGR)
	webpack: (config) => {
		// SVGR: import *.svg as React components
		const fileLoaderRule = config.module.rules.find((rule: any) => rule.test?.test?.(".svg"));
		config.module.rules.push(
			// Re-apply the existing file loader for *.svg?url imports
			{
				...fileLoaderRule,
				test: /\.svg$/i,
				resourceQuery: /url/, // e.g. import icon from './icon.svg?url'
			},
			// Convert all other *.svg imports to React components
			{
				test: /\.svg$/i,
				issuer: fileLoaderRule.issuer,
				resourceQuery: { not: [...fileLoaderRule.resourceQuery.not, /url/] },
				use: ["@svgr/webpack"],
			}
		);
		fileLoaderRule.exclude = /\.svg$/i;

		return config;
	},
};

export default withNextIntl(nextConfig);
