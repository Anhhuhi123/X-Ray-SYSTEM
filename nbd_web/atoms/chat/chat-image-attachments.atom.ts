"use client";

import { atom } from "jotai";

export interface SelectedChatImageAttachment {
	id: string;
	file: File;
	name: string;
	type: string;
	size: number;
}

export interface ChatImageAttachmentInfo {
	id: string;
	name: string;
	type: string;
	size: number;
}

export const selectedChatImageAttachmentsAtom = atom<SelectedChatImageAttachment[]>([]);

export const messageImageAttachmentsMapAtom = atom<Record<string, ChatImageAttachmentInfo[]>>({});

export const clearSelectedChatImageAttachmentsAtom = atom(null, (_, set) => {
	set(selectedChatImageAttachmentsAtom, []);
});