import { atomWithQuery } from "jotai-tanstack-query";
import { adminApiService } from "@/lib/apis/admin-api.service";
import { cacheKeys } from "@/lib/query-client/cache-keys";
import { getBearerToken } from "@/lib/auth-utils";

export const adminOverviewStatsAtom = atomWithQuery(() => ({
	queryKey: [...cacheKeys.user.current(), "admin", "overview"],
	staleTime: 60 * 1000, // 1 minute
	enabled: !!getBearerToken(),
	queryFn: async () => adminApiService.getOverviewStats(),
}));

export const adminUsersQueryAtom = (page: number, pageSize: number, search?: string) => 
	atomWithQuery(() => ({
		queryKey: [...cacheKeys.user.current(), "admin", "users", page, pageSize, search],
		staleTime: 60 * 1000,
		enabled: !!getBearerToken(),
		queryFn: async () => adminApiService.getUsers(page, pageSize, search),
	}));

export const adminConversationsQueryAtom = (page: number, pageSize: number, search?: string) => 
	atomWithQuery(() => ({
		queryKey: [...cacheKeys.user.current(), "admin", "conversations", page, pageSize, search],
		staleTime: 60 * 1000,
		enabled: !!getBearerToken(),
		queryFn: async () => adminApiService.getConversations(page, pageSize, search),
	}));

