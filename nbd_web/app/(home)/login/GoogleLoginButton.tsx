"use client";

import { motion } from "motion/react";
import { useTranslations } from "next-intl";
import { Logo } from "@/components/Logo";
import { trackLoginAttempt } from "@/lib/posthog/events";
import { AmbientBackground } from "./AmbientBackground";

export function GoogleLoginButton() {
	const t = useTranslations("auth");

	const handleGoogleLogin = () => {
		// Track Google login attempt
		trackLoginAttempt("google");

		// IMPORTANT: Use the redirect-based authorize endpoint for cross-origin OAuth
		// This fixes CSRF cookie issues in Firefox/Safari where cookies set via
		// cross-origin fetch requests may not be sent on subsequent redirects.
		// The authorize-redirect endpoint does a server-side redirect to Google
		// and sets the CSRF cookie properly for same-site context.
		window.location.href = `${process.env.NEXT_PUBLIC_FASTAPI_BACKEND_URL}/auth/google/authorize-redirect`;
	};
	return (
		<div className="relative w-full overflow-hidden">
			<AmbientBackground />
			<div className="mx-auto flex h-screen max-w-lg flex-col items-center justify-center px-6 md:px-0">
				<Logo className="h-16 w-16 md:h-32 md:w-32 rounded-full my-4 md:my-8 transition-all" />
				{/* <h1 className="my-8 text-xl font-bold text-neutral-800 dark:text-neutral-100 md:text-4xl">
					Login
				</h1> */}
				{/* 
				<motion.div
					initial={{ opacity: 0, y: -5 }}
					animate={{ opacity: 1, y: 0 }}
					transition={{ duration: 0.3 }}
					className="mb-4 w-full overflow-hidden rounded-lg border border-yellow-200 bg-yellow-50 text-yellow-900 shadow-sm dark:border-yellow-900/30 dark:bg-yellow-900/20 dark:text-yellow-200"
				>
					<motion.div
						className="flex items-center gap-2 p-4"
						initial={{ x: -5 }}
						animate={{ x: 0 }}
						transition={{ delay: 0.1, duration: 0.2 }}
					>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							width="16"
							height="16"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							strokeWidth="2"
							strokeLinecap="round"
							strokeLinejoin="round"
							className="flex-shrink-0"
						>
							<title>Google Logo</title>
							<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
							<line x1="12" y1="9" x2="12" y2="13" />
							<line x1="12" y1="17" x2="12.01" y2="17" />
						</svg>
						<div className="ml-1">
							<p className="text-sm font-medium">
								{t("cloud_dev_notice")}{" "}
								<a
									href="/docs"
									className="text-blue-600 underline dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300"
								>
									{t("docs")}
								</a>{" "}
								{t("cloud_dev_self_hosted")}
							</p>
						</div>
					</motion.div>
				</motion.div> */}

				<motion.button
					whileHover={{ scale: 1.02 }}
					whileTap={{ scale: 0.98 }}
					className="group/btn relative flex w-full items-center justify-center space-x-2 rounded-lg bg-white px-6 py-3 md:py-4 text-neutral-700 shadow-lg transition-all duration-200 hover:shadow-xl dark:bg-neutral-800 dark:text-neutral-200"
					onClick={handleGoogleLogin}
				>
					<div className="absolute inset-0 h-full w-full transform opacity-0 transition duration-200 group-hover/btn:opacity-100">
						<div className="absolute -left-px -top-px h-4 w-4 rounded-tl-lg border-l-2 border-t-2 border-blue-500 bg-transparent transition-all duration-200 group-hover/btn:-left-2 group-hover/btn:-top-2"></div>
						<div className="absolute -right-px -top-px h-4 w-4 rounded-tr-lg border-r-2 border-t-2 border-blue-500 bg-transparent transition-all duration-200 group-hover/btn:-right-2 group-hover/btn:-top-2"></div>
						<div className="absolute -bottom-px -left-px h-4 w-4 rounded-bl-lg border-b-2 border-l-2 border-blue-500 bg-transparent transition-all duration-200 group-hover/btn:-bottom-2 group-hover/btn:-left-2"></div>
						<div className="absolute -bottom-px -right-px h-4 w-4 rounded-br-lg border-b-2 border-r-2 border-blue-500 bg-transparent transition-all duration-200 group-hover/btn:-bottom-2 group-hover/btn:-right-2"></div>
					</div>
					<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" className="h-5 w-5 mr-2">
						<path fill="#FFC107" d="M43.611 20.083H42V20H24v8h11.303c-1.649 4.657-6.08 8-11.303 8c-6.627 0-12-5.373-12-12s5.373-12 12-12c3.059 0 5.842 1.154 7.961 3.039l5.657-5.657C34.046 6.053 29.268 4 24 4C12.955 4 4 12.955 4 24s8.955 20 20 20s20-8.955 20-20c0-1.341-.138-2.65-.389-3.917z"/>
						<path fill="#FF3D00" d="M6.306 14.691l6.571 4.819C14.655 15.108 18.961 12 24 12c3.059 0 5.842 1.154 7.961 3.039l5.657-5.657C34.046 6.053 29.268 4 24 4C16.318 4 9.656 8.337 6.306 14.691z"/>
						<path fill="#4CAF50" d="M24 44c5.166 0 9.86-1.977 13.409-5.192l-6.19-5.238A11.91 11.91 0 0 1 24 36c-5.222 0-9.654-3.343-11.303-8l-6.571 4.819C9.656 39.663 16.318 44 24 44z"/>
						<path fill="#1976D2" d="M43.611 20.083H42V20H24v8h11.303a12.04 12.04 0 0 1-4.087 5.571l.003-.002l6.19 5.238C36.971 39.205 44 34 44 24c0-1.341-.138-2.65-.389-3.917z"/>
					</svg>
					<span className="text-base font-medium">{t("continue_with_google")}</span>
				</motion.button>
			</div>
		</div>
	);
}
