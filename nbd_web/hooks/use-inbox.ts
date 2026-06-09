"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { InboxItem, NotificationCategory } from "@/contracts/types/inbox.types";
import { notificationsApiService } from "@/lib/apis/notifications-api.service";

export type {
	InboxItem,
	InboxItemTypeEnum,
	NotificationCategory,
} from "@/contracts/types/inbox.types";

const INITIAL_PAGE_SIZE = 50;
const SCROLL_PAGE_SIZE = 30;
const SYNC_WINDOW_DAYS = 4;

const CATEGORY_TYPE_SQL: Record<NotificationCategory, string> = {
	comments: "AND type IN ('new_mention', 'comment_reply')",
	status:
		"AND type IN ('connector_indexing', 'connector_deletion', 'document_processing', 'page_limit_exceeded')",
};

/**
 * Calculate the cutoff date for sync window.
 * Rounds to the start of the day (midnight UTC) to ensure stable values
 * across re-renders.
 */
function getSyncCutoffDate(): string {
	const cutoff = new Date();
	cutoff.setDate(cutoff.getDate() - SYNC_WINDOW_DAYS);
	cutoff.setUTCHours(0, 0, 0, 0);
	return cutoff.toISOString();
}

/**
 * Hook for managing inbox items with API-first architecture + Electric real-time deltas.
 *
 * Architecture (Documents pattern, per-tab):
 * 1. API is the PRIMARY data source — fetches first page on mount with category filter
 * 2. Electric provides REAL-TIME updates (new items, status changes, read state)
 * 3. Baseline pattern prevents duplicates between API and Electric
 * 4. Electric sync shape is SHARED across instances (client-level caching)
 *    — each instance creates its own type-filtered live queries
 *
 * Unread count strategy:
 * - API provides the category-filtered total on mount (ground truth across all time)
 * - Electric live query counts unread within SYNC_WINDOW_DAYS (filtered by type)
 * - olderUnreadOffsetRef bridges the gap: total = offset + recent
 * - Optimistic updates adjust both the count and the offset (for old items)
 *
 * @param userId - The user ID to fetch inbox items for
 * @param searchSpaceId - The search space ID to filter inbox items
 * @param category - Which tab: "comments" or "status"
 */
export function useInbox(
	userId: string | null,
	searchSpaceId: number | null,
	category: NotificationCategory,
	prefetchedUnread?: { total_unread: number; recent_unread: number } | null,
	prefetchedUnreadReady = true
) {
	const [inboxItems, setInboxItems] = useState<InboxItem[]>([]);
	const [loading, setLoading] = useState(true);
	const [loadingMore, setLoadingMore] = useState(false);
	const [hasMore, setHasMore] = useState(false);
	const [error, setError] = useState<Error | null>(null);
	const [unreadCount, setUnreadCount] = useState(0);

	const initialLoadDoneRef = useRef(false);

	// EFFECT 1: Fetch first page + unread count from API with category filter.
	// When prefetchedUnreadReady=false, we wait for the batch query to settle
	// before deciding whether we need an individual unread-count fallback call.
	useEffect(() => {
		if (!userId || !searchSpaceId) return;
		if (!prefetchedUnreadReady) return;

		let cancelled = false;

		setLoading(true);
		setInboxItems([]);
		setHasMore(false);
		initialLoadDoneRef.current = false;

		const fetchInitialData = async () => {
			try {
				const notificationsPromise = notificationsApiService.getNotifications({
					queryParams: {
						search_space_id: searchSpaceId,
						category,
						limit: INITIAL_PAGE_SIZE,
					},
				});

				// Use prefetched counts when available, otherwise fetch individually.
				const unreadPromise = prefetchedUnread
					? Promise.resolve(prefetchedUnread)
					: notificationsApiService.getUnreadCount(searchSpaceId, undefined, category);

				const [notificationsResponse, unreadResponse] = await Promise.all([
					notificationsPromise,
					unreadPromise,
				]);

				if (cancelled) return;

				setInboxItems(notificationsResponse.items);
				setHasMore(notificationsResponse.has_more);
				setUnreadCount(unreadResponse.total_unread);
				setError(null);
				initialLoadDoneRef.current = true;
			} catch (err) {
				if (cancelled) return;
				console.error(`[useInbox:${category}] Initial load failed:`, err);
				setError(err instanceof Error ? err : new Error("Failed to load notifications"));
			} finally {
				if (!cancelled) setLoading(false);
			}
		};

		fetchInitialData();
		return () => {
			cancelled = true;
		};
	}, [userId, searchSpaceId, category, prefetchedUnread, prefetchedUnreadReady]);



	// Load more pages via API (cursor-based using before_date)
	const loadMore = useCallback(async () => {
		if (loadingMore || !hasMore || !userId || !searchSpaceId) return;

		setLoadingMore(true);
		try {
			const oldestItem = inboxItems.length > 0 ? inboxItems[inboxItems.length - 1] : null;
			const beforeDate = oldestItem?.created_at ?? undefined;

			const response = await notificationsApiService.getNotifications({
				queryParams: {
					search_space_id: searchSpaceId,
					category,
					before_date: beforeDate,
					limit: SCROLL_PAGE_SIZE,
				},
			});

			const newItems = response.items;

			setInboxItems((prev) => {
				const existingIds = new Set(prev.map((d) => d.id));
				const deduped = newItems.filter((d) => !existingIds.has(d.id));
				return [...prev, ...deduped];
			});
			setHasMore(response.has_more);
		} catch (err) {
			console.error(`[useInbox:${category}] Load more failed:`, err);
		} finally {
			setLoadingMore(false);
		}
	}, [loadingMore, hasMore, userId, searchSpaceId, inboxItems, category]);

	// Mark single item as read with optimistic update
	const markAsRead = useCallback(
		async (itemId: number) => {
			const item = inboxItems.find((i) => i.id === itemId);
			if (!item || item.read) return true;

			setInboxItems((prev) => prev.map((i) => (i.id === itemId ? { ...i, read: true } : i)));
			setUnreadCount((prev) => Math.max(0, prev - 1));

			try {
				const result = await notificationsApiService.markAsRead({ notificationId: itemId });
				if (!result.success) {
					setInboxItems((prev) => prev.map((i) => (i.id === itemId ? { ...i, read: false } : i)));
					setUnreadCount((prev) => prev + 1);
				}
				return result.success;
			} catch (err) {
				console.error("Failed to mark as read:", err);
				setInboxItems((prev) => prev.map((i) => (i.id === itemId ? { ...i, read: false } : i)));
				setUnreadCount((prev) => prev + 1);
				return false;
			}
		},
		[inboxItems]
	);

	// Mark all as read with optimistic update
	const markAllAsRead = useCallback(async () => {
		const prevItems = inboxItems;
		const prevCount = unreadCount;

		setInboxItems((prev) => prev.map((item) => ({ ...item, read: true })));
		setUnreadCount(0);

		try {
			const result = await notificationsApiService.markAllAsRead();
			if (!result.success) {
				setInboxItems(prevItems);
				setUnreadCount(prevCount);
			}
			return result.success;
		} catch (err) {
			console.error("Failed to mark all as read:", err);
			setInboxItems(prevItems);
			setUnreadCount(prevCount);
			return false;
		}
	}, [inboxItems, unreadCount]);

	return {
		inboxItems,
		unreadCount,
		markAsRead,
		markAllAsRead,
		loading,
		loadingMore,
		hasMore,
		loadMore,
		error,
	};
}
