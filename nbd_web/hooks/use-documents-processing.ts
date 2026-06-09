"use client";

export type DocumentsProcessingStatus = "idle" | "processing" | "success" | "error";

/**
 * Returns the processing status of documents in the search space.
 * Simplified to return "idle" since Electric SQL real-time replication is removed.
 */
export function useDocumentsProcessing(searchSpaceId: number | null): DocumentsProcessingStatus {
	return "idle";
}
