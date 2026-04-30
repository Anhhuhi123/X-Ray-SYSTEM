import { atomWithQuery } from "jotai-tanstack-query";
import { activeSearchSpaceIdAtom } from "@/atoms/search-spaces/search-space-query.atoms";
import { membersApiService } from "@/lib/apis/members-api.service";
import { AuthorizationError, NotFoundError } from "@/lib/error";
import { cacheKeys } from "@/lib/query-client/cache-keys";

export const membersAtom = atomWithQuery((get) => {
	const searchSpaceId = get(activeSearchSpaceIdAtom);

	return {
		queryKey: cacheKeys.members.all(searchSpaceId?.toString() ?? ""),
		enabled: !!searchSpaceId,
		staleTime: 3 * 1000, // 3 seconds - short staleness for live collaboration
		refetchInterval: 2 * 60 * 1000, // 2 minutes
		queryFn: async () => {
			if (!searchSpaceId) {
				return [];
			}
			try {
				return await membersApiService.getMembers({
					search_space_id: Number(searchSpaceId),
				});
			} catch (error) {
				// If the current URL points to a deleted/inaccessible space, avoid
				// crashing the dashboard and let layout redirect to a valid space.
				if (error instanceof NotFoundError || error instanceof AuthorizationError) {
					return [];
				}
				throw error;
			}
		},
	};
});

export const myAccessAtom = atomWithQuery((get) => {
	const searchSpaceId = get(activeSearchSpaceIdAtom);

	return {
		queryKey: cacheKeys.members.myAccess(searchSpaceId?.toString() ?? ""),
		enabled: !!searchSpaceId,
		staleTime: 5 * 60 * 1000, // 5 minutes
		queryFn: async () => {
			if (!searchSpaceId) {
				return null;
			}
			try {
				return await membersApiService.getMyAccess({
					search_space_id: Number(searchSpaceId),
				});
			} catch (error) {
				// Treat missing access as "no access" instead of bubbling to error boundary.
				if (error instanceof NotFoundError || error instanceof AuthorizationError) {
					return null;
				}
				throw error;
			}
		},
	};
});
