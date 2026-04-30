"use client";

import { NextIntlClientProvider } from "next-intl";
import { useLocaleContext } from "@/contexts/LocaleContext";

/**
 * I18n Provider component
 * Wraps NextIntlClientProvider with dynamic locale and messages from LocaleContext
 */
export function I18nProvider({ children }: { children: React.ReactNode }) {
	const { locale, messages } = useLocaleContext();

	// Resolve the client's time zone to avoid next-intl ENVIRONMENT_FALLBACK
	const timeZone =
		typeof Intl !== "undefined" && typeof Intl.DateTimeFormat === "function"
			? Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC"
			: "UTC";

	return (
		<NextIntlClientProvider messages={messages} locale={locale} timeZone={timeZone}>
			{children}
		</NextIntlClientProvider>
	);
}
