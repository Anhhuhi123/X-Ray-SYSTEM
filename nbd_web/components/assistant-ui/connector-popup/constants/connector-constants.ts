import { EnumConnectorName } from "@/contracts/enums/connector";

// OAuth Connectors (Quick Connect)
export const OAUTH_CONNECTORS = [
	{
		id: "google-drive-connector",
		title: "Google Drive",
		description: "Search your Drive files",
		connectorType: EnumConnectorName.GOOGLE_DRIVE_CONNECTOR,
		authEndpoint: "/api/v1/auth/google/drive/connector/add/",
	},
] as const;

// Content Sources (tools that extract and import content from external sources)
export const CRAWLERS = [
	{
		id: "webcrawler-connector",
		title: "Web Pages",
		description: "Index and periodically sync web content",
		connectorType: EnumConnectorName.WEBCRAWLER_CONNECTOR,
	},
] as const;

// Non-OAuth Connectors (redirect to old connector config pages)
export const OTHER_CONNECTORS: Array<{
	id: string;
	title: string;
	description: string;
	connectorType: EnumConnectorName;
	selfHostedOnly?: boolean;
}> = [];

// Composio Connectors - Individual entries for each supported toolkit
export const COMPOSIO_CONNECTORS = [
	{
		id: "composio-googledrive",
		title: "Google Drive",
		description: "Search your Drive files via Composio",
		connectorType: EnumConnectorName.COMPOSIO_GOOGLE_DRIVE_CONNECTOR,
		authEndpoint: "/api/v1/auth/composio/connector/add/?toolkit_id=googledrive",
	},
] as const;

// Composio Toolkits (available integrations via Composio)
export const COMPOSIO_TOOLKITS = [
	{
		id: "googledrive",
		name: "Google Drive",
		description: "Search your Drive files",
		isIndexable: true,
	},
] as const;

export interface AutoIndexConfig {
	daysBack: number;
	daysForward: number;
	frequencyMinutes: number;
	syncDescription: string;
}

export const AUTO_INDEX_DEFAULTS: Record<string, AutoIndexConfig> = {
};

export const AUTO_INDEX_CONNECTOR_TYPES = new Set<string>(Object.keys(AUTO_INDEX_DEFAULTS));

// Re-export IndexingConfigState from schemas for backward compatibility
export type { IndexingConfigState } from "./connector-popup.schemas";
