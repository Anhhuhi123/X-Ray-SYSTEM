"use client";

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
			</div>
		</div>
	);
}
