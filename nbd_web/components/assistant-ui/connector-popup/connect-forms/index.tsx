import type { FC } from "react";
import { MCPConnectForm } from "./components/mcp-connect-form";
import { ObsidianConnectForm } from "./components/obsidian-connect-form";

export interface ConnectFormProps {
	onSubmit: (data: {
		name: string;
		connector_type: string;
		config: Record<string, unknown>;
		is_indexable: boolean;
		is_active: boolean;
		last_indexed_at: null;
		periodic_indexing_enabled: boolean;
		indexing_frequency_minutes: number | null;
		next_scheduled_at: null;
		startDate?: Date;
		endDate?: Date;
		periodicEnabled?: boolean;
		frequencyMinutes?: string;
	}) => Promise<void>;
	onBack: () => void;
	isSubmitting: boolean;
	onFormSubmit?: () => void;
}

export type ConnectFormComponent = FC<ConnectFormProps>;

/**
 * Factory function to get the appropriate connect form component for a connector type
 */
export function getConnectFormComponent(connectorType: string): ConnectFormComponent | null {
	switch (connectorType) {
		case "MCP_CONNECTOR":
			return MCPConnectForm;
		case "OBSIDIAN_CONNECTOR":
			return ObsidianConnectForm;
		// Add other connector types here as needed
		default:
			return null;
	}
}
