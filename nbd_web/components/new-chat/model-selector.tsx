"use client";

import { useAtomValue } from "jotai";
import { Edit3, Plus, Settings2, Sparkles } from "lucide-react";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import { updateLLMPreferencesMutationAtom } from "@/atoms/new-llm-config/new-llm-config-mutation.atoms";
import {
	globalNewLLMConfigsAtom,
	llmPreferencesAtom,
	newLLMConfigsAtom,
} from "@/atoms/new-llm-config/new-llm-config-query.atoms";
import { activeSearchSpaceIdAtom } from "@/atoms/search-spaces/search-space-query.atoms";
import type {
	GlobalNewLLMConfig,
	NewLLMConfigPublic,
} from "@/contracts/types/new-llm-config.types";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
	Popover,
	PopoverContent,
	PopoverTrigger,
} from "@/components/ui/popover";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { Spinner } from "@/components/ui/spinner";
import { getProviderIcon } from "@/lib/provider-icons";
import { cn } from "@/lib/utils";

interface ModelSelectorProps {
	onEditLLM: (config: NewLLMConfigPublic | GlobalNewLLMConfig, global: boolean) => void;
	onAddNewLLM: () => void;
	className?: string;
}

function ModelListSection({
	title,
	items,
	activeId,
	isSwitching,
	onSelect,
	onEdit,
}: {
	title: string;
	items: Array<NewLLMConfigPublic | GlobalNewLLMConfig>;
	activeId?: number | null;
	isSwitching: boolean;
	onSelect: (config: NewLLMConfigPublic | GlobalNewLLMConfig) => void;
	onEdit: (config: NewLLMConfigPublic | GlobalNewLLMConfig) => void;
}) {
	return (
		<div className="space-y-2">
			<p className="text-xs font-medium text-muted-foreground">{title}</p>
			{items.length === 0 ? (
				<p className="text-xs text-muted-foreground">No models found.</p>
			) : (
				<div className="space-y-1">
					{items.map((config) => (
						<div
							key={config.id}
							role="button"
							tabIndex={0}
							onClick={() => onSelect(config)}
							onKeyDown={(e) => {
								if (e.key === "Enter" || e.key === " ") {
									e.preventDefault();
									onSelect(config);
								}
							}}
							className={cn(
								"group flex items-center justify-between rounded-md px-2 py-2 transition-colors hover:bg-muted/60",
								activeId === config.id && "bg-muted"
							)}
						>
							<div className="min-w-0 flex items-center gap-2">
								{getProviderIcon(config.provider, {
									isAutoMode: "is_auto_mode" in config ? config.is_auto_mode : false,
									className: "h-3.5 w-3.5 shrink-0",
								})}
								<div className="min-w-0">
									<div className="flex items-center gap-1.5">
										<p className="truncate text-sm font-medium">{config.name}</p>
										{activeId === config.id && (
											<span className="text-[10px] rounded bg-emerald-500/15 px-1.5 py-0.5 text-emerald-600 dark:text-emerald-400">
												Active
											</span>
										)}
									</div>
									<p className="truncate text-xs text-muted-foreground">{config.model_name}</p>
								</div>
							</div>
							<Button
								variant="ghost"
								size="icon"
								className="h-7 w-7 opacity-0 group-hover:opacity-100"
								onClick={(e) => {
									e.stopPropagation();
									onEdit(config);
								}}
								disabled={isSwitching}
							>
								<Edit3 className="h-3.5 w-3.5" />
							</Button>
						</div>
					))}
				</div>
			)}
		</div>
	);
}

export function ModelSelector({ onEditLLM, onAddNewLLM, className }: ModelSelectorProps) {
	const [open, setOpen] = useState(false);
	const {
		data: userConfigs = [],
		isFetching: userLoading,
	} = useAtomValue(newLLMConfigsAtom);
	const {
		data: globalConfigs = [],
		isFetching: globalLoading,
	} = useAtomValue(globalNewLLMConfigsAtom);
	const { data: preferences } = useAtomValue(llmPreferencesAtom);
	const searchSpaceId = useAtomValue(activeSearchSpaceIdAtom);
	const { mutateAsync: updatePreferences, isPending: isSwitching } = useAtomValue(
		updateLLMPreferencesMutationAtom
	);

	const hasAnyConfigs = useMemo(
		() => userConfigs.length > 0 || globalConfigs.length > 0,
		[userConfigs, globalConfigs]
	);

	const currentConfig = useMemo(() => {
		const id = preferences?.agent_llm_id;
		if (id === null || id === undefined) return null;
		const globalMatch = globalConfigs.find((c) => c.id === id);
		if (globalMatch) return globalMatch;
		return userConfigs.find((c) => c.id === id) ?? null;
	}, [preferences, globalConfigs, userConfigs]);

	const handleSwitchModel = async (config: NewLLMConfigPublic | GlobalNewLLMConfig) => {
		if (!searchSpaceId) {
			toast.error("No search space selected");
			return;
		}
		if (preferences?.agent_llm_id === config.id) {
			setOpen(false);
			return;
		}

		try {
			await updatePreferences({
				search_space_id: Number(searchSpaceId),
				data: { agent_llm_id: config.id },
			});
			toast.success(`Switched to ${config.name}`);
			setOpen(false);
		} catch {
			toast.error("Failed to switch model");
		}
	};

	return (
		<Popover open={open} onOpenChange={setOpen}>
			<PopoverTrigger asChild>
				<Button variant="outline" size="sm" className={cn("max-w-[220px]", className)}>
					{isSwitching ? (
						<Spinner size="sm" />
					) : (
						<Sparkles className="h-4 w-4" />
					)}
					<span className="truncate">
						{currentConfig ? currentConfig.name : "Models"}
					</span>
				</Button>
			</PopoverTrigger>
			<PopoverContent className="w-[360px] p-0" align="start" sideOffset={8}>
				<Card className="border-0 shadow-none">
					<CardHeader className="pb-3">
						<CardTitle className="flex items-center gap-2 text-sm">
							<Settings2 className="h-4 w-4" />
							Model Manager
						</CardTitle>
					</CardHeader>
					<CardContent className="space-y-3">
						<Button
							className="w-full"
							size="sm"
							onClick={() => {
								onAddNewLLM();
								setOpen(false);
							}}
						>
							<Plus className="mr-1.5 h-4 w-4" />
							Add LLM Model
						</Button>

						<Separator />

						{(userLoading || globalLoading) && (
							<div className="space-y-2">
								<Skeleton className="h-8 w-full" />
								<Skeleton className="h-8 w-full" />
								<Skeleton className="h-8 w-full" />
							</div>
						)}

						{!userLoading && !globalLoading && !hasAnyConfigs && (
							<p className="text-xs text-muted-foreground">No models available yet.</p>
						)}

						{!userLoading && !globalLoading && hasAnyConfigs && (
							<div className="space-y-3">
								<ModelListSection
									title="Global Models"
									items={globalConfigs}
									activeId={preferences?.agent_llm_id ?? null}
									isSwitching={isSwitching}
									onSelect={handleSwitchModel}
									onEdit={(config) => {
										onEditLLM(config, true);
										setOpen(false);
									}}
								/>
								<Separator />
								<ModelListSection
									title="Your Models"
									items={userConfigs}
									activeId={preferences?.agent_llm_id ?? null}
									isSwitching={isSwitching}
									onSelect={handleSwitchModel}
									onEdit={(config) => {
										onEditLLM(config, false);
										setOpen(false);
									}}
								/>
							</div>
						)}
					</CardContent>
				</Card>
			</PopoverContent>
		</Popover>
	);
}
