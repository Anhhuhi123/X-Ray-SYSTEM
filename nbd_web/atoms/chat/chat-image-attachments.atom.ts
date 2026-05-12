"use client";

import { atom } from "jotai";

export interface SelectedChatImageAttachment {
	id: string;
	file: File;
	name: string;
	type: string;
	size: number;
	image_path: string;
}

export interface ChatImageAttachmentInfo {
	id: string;
	name: string;
	type: string;
	size: number;
	image_path: string;
}

export interface ChatInferenceOutputPrediction {
	label_name: string;
	probability: number;
	threshold_used: number;
	is_positive: boolean;
}

export interface ChatInferenceOutputInfo {
	request_id: string;
	image_path: string;
	image_url: string;
	filename: string;
	threshold: number;
	inference_time_ms: number;
	predictions: ChatInferenceOutputPrediction[];
	heatmap_path: string | null;
	bbox_path: string | null;
	crop_path: string | null;
	heatmap_url: string | null;
	bbox_url: string | null;
	crop_url: string | null;
	positive_labels: string[];
	top_predictions: ChatInferenceOutputPrediction[];
}

export const selectedChatImageAttachmentsAtom = atom<SelectedChatImageAttachment[]>([]);

export const messageImageAttachmentsMapAtom = atom<Record<string, ChatImageAttachmentInfo[]>>({});

export const messageInferenceOutputsMapAtom = atom<Record<string, ChatInferenceOutputInfo[]>>({});

export const clearSelectedChatImageAttachmentsAtom = atom(null, (_, set) => {
	set(selectedChatImageAttachmentsAtom, []);
});