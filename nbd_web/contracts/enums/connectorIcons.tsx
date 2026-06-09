import { IconUsersGroup } from "@tabler/icons-react";
import {
	BookOpen,
	File,
	FileText,
	Globe,
	Microscope,
	Search,
	Sparkles,
	Telescope,
	Webhook,
} from "lucide-react";
import Image from "next/image";
import { EnumConnectorName } from "./connector";

export const getConnectorIcon = (connectorType: EnumConnectorName | string, className?: string) => {
	const iconProps = { className: className || "h-4 w-4" };
	const imgProps = {
		className: `${className || "h-5 w-5"} select-none pointer-events-none`,
		width: 20,
		height: 20,
		draggable: false as const,
	};

	switch (connectorType) {
		case EnumConnectorName.MCP_CONNECTOR:
			return <Image src="/connectors/modelcontextprotocol.svg" alt="MCP" {...imgProps} />;
		case EnumConnectorName.OBSIDIAN_CONNECTOR:
			return <Image src="/connectors/obsidian.svg" alt="Obsidian" {...imgProps} />;
		case EnumConnectorName.COMPOSIO_GOOGLE_DRIVE_CONNECTOR:
			return <Image src="/connectors/google-drive.svg" alt="Google Drive" {...imgProps} />;
		case "CRAWLED_URL":
			return <Globe {...iconProps} />;
		case "ZOOM":
		case "zoom":
			return <Image src="/connectors/zoom.svg" alt="Zoom" {...imgProps} />;
		case "FILE":
			return <File {...iconProps} />;
		case "COMPOSIO_GOOGLE_DRIVE_CONNECTOR":
			return <Image src="/connectors/google-drive.svg" alt="Google Drive" {...imgProps} />;
		case "NOTE":
			return <FileText {...iconProps} />;
		case "EXTENSION":
			return <Webhook {...iconProps} />;
		case "NFD_DOCS":
			return <BookOpen {...iconProps} />;
		case "DEEP":
			return <Sparkles {...iconProps} />;
		case "DEEPER":
			return <Microscope {...iconProps} />;
		case "DEEPEST":
			return <Telescope {...iconProps} />;
		default:
			return <Search {...iconProps} />;
	}
};
