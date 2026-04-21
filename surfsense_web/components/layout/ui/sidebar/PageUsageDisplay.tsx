"use client";

import Link from "next/link";
import { Progress } from "@/components/ui/progress";

interface PageUsageDisplayProps {
	pagesUsed: number;
	pagesLimit: number;
}

export function PageUsageDisplay({ pagesUsed, pagesLimit }: PageUsageDisplayProps) {
	const usagePercentage = (pagesUsed / pagesLimit) * 100;

	return (
		<div className="px-3 py-3 border-t">
			<div className="space-y-2">
				<div className="flex justify-between items-center text-xs">
					<span className="text-muted-foreground">
						{pagesUsed.toLocaleString()} / {pagesLimit.toLocaleString()} pages
					</span>
					<span className="font-medium">{usagePercentage.toFixed(0)}%</span>
				</div>
				<Progress value={usagePercentage} className="h-1.5" />
				<Link
					href="/contact"
					className="group flex items-center justify-between rounded-md px-1.5 py-1 -mx-1.5 transition-colors hover:bg-accent"
				>
					<span className="flex items-center gap-1.5 text-xs text-muted-foreground group-hover:text-accent-foreground">
						Contact us to upgrade
					</span>
					<span className="text-[10px] font-semibold uppercase tracking-wide text-emerald-600">
						PRO
					</span>
				</Link>
			</div>
		</div>
	);
}
