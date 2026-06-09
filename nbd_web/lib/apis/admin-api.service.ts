import { z } from "zod";
import { baseApiService } from "./base-api.service";

export const overviewStatsSchema = z.object({
	total_users: z.number(),
	today_users: z.number(),
	week_users: z.number(),
	total_requests: z.number(),
	today_requests: z.number(),
	week_requests: z.number(),
	total_conversations: z.number(),
	active_conversations: z.number(),
	avg_response_time: z.number(),
	success_rate: z.number(),
	error_rate: z.number(),
	input_tokens: z.number(),
	output_tokens: z.number(),
	total_tokens: z.number(),
});

export type OverviewStats = z.infer<typeof overviewStatsSchema>;

export const adminUserItemSchema = z.object({
	id: z.string(),
	email: z.string(),
	name: z.string().nullable(),
	status: z.string(),
	joined_date: z.string(),
	last_active: z.string().nullable(),
	total_conversations: z.number(),
	total_requests: z.number(),
});

export const adminUsersResponseSchema = z.object({
	items: z.array(adminUserItemSchema),
	total: z.number(),
	page: z.number(),
	page_size: z.number(),
});

export type AdminUserItem = z.infer<typeof adminUserItemSchema>;
export type AdminUsersResponse = z.infer<typeof adminUsersResponseSchema>;

export const adminConversationItemSchema = z.object({
	id: z.string(),
	messageId: z.string(),
	userId: z.string().nullable(),
	user: z.string().nullable(),
	timestamp: z.string(),
	question: z.string(),
	answerPreview: z.string(),
	model: z.string(),
	responseTime: z.string(),
	tokens: z.object({
		input: z.number(),
		output: z.number(),
		total: z.number(),
	}),
	status: z.string(),
	fullAnswer: z.string().nullable(),
});

export const adminConversationsResponseSchema = z.object({
	items: z.array(adminConversationItemSchema),
	total: z.number(),
	page: z.number(),
	page_size: z.number(),
});

export type AdminConversationItem = z.infer<typeof adminConversationItemSchema>;
export type AdminConversationsResponse = z.infer<typeof adminConversationsResponseSchema>;

class AdminApiService {
	getOverviewStats = async () => {
		return baseApiService.get(`/api/v1/admin/overview`, overviewStatsSchema);
	};

	getUsers = async (page: number = 1, pageSize: number = 10, search?: string) => {
		const params = new URLSearchParams({
			page: page.toString(),
			page_size: pageSize.toString(),
		});
		if (search) params.append("search", search);
		
		return baseApiService.get(`/api/v1/admin/users?${params.toString()}`, adminUsersResponseSchema);
	};

	getConversations = async (page: number = 1, pageSize: number = 10, search?: string) => {
		const params = new URLSearchParams({
			page: page.toString(),
			page_size: pageSize.toString(),
		});
		if (search) params.append("search", search);
		
		return baseApiService.get(`/api/v1/admin/conversations?${params.toString()}`, adminConversationsResponseSchema);
	};
}

export const adminApiService = new AdminApiService();
