"use client";

import { useCallback, useState } from "react";
import type {
	GlobalNewLLMConfig,
	NewLLMConfigPublic,
} from "@/contracts/types/new-llm-config.types";
import { ModelSelector } from "@/components/new-chat/model-selector";
import { ModelConfigDialog } from "./model-config-dialog";

interface ChatHeaderProps {
	searchSpaceId: number;
	className?: string;
}

export function ChatHeader({ searchSpaceId, className }: ChatHeaderProps) {
	// LLM config dialog state
	const [dialogOpen, setDialogOpen] = useState(false);
	const [selectedConfig, setSelectedConfig] = useState<
		NewLLMConfigPublic | GlobalNewLLMConfig | null
	>(null);
	const [isGlobal, setIsGlobal] = useState(false);
	const [dialogMode, setDialogMode] = useState<"create" | "edit" | "view">("view");

	// LLM handlers
	const handleEditLLMConfig = useCallback(
		(config: NewLLMConfigPublic | GlobalNewLLMConfig, global: boolean) => {
			setSelectedConfig(config);
			setIsGlobal(global);
			setDialogMode(global ? "view" : "edit");
			setDialogOpen(true);
		},
		[]
	);

	const handleAddNewLLM = useCallback(() => {
		setSelectedConfig(null);
		setIsGlobal(false);
		setDialogMode("create");
		setDialogOpen(true);
	}, []);

	const handleDialogClose = useCallback((open: boolean) => {
		setDialogOpen(open);
		if (!open) setSelectedConfig(null);
	}, []);

	return (
		<div className="flex items-center gap-2">
			<ModelSelector
				onEditLLM={handleEditLLMConfig}
				onAddNewLLM={handleAddNewLLM}
				className={className}
			/>
			<ModelConfigDialog
				open={dialogOpen}
				onOpenChange={handleDialogClose}
				config={selectedConfig}
				isGlobal={isGlobal}
				searchSpaceId={searchSpaceId}
				mode={dialogMode}
			/>
		</div>
	);
}
