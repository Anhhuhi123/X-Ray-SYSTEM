"use client";

import { useAtomValue } from "jotai";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Users, MessageSquare, Activity, Zap, ArrowUpRight, ArrowDownRight, Loader2 } from "lucide-react";
import dynamic from "next/dynamic";

const RequestTrendChart = dynamic(() => import("../components/overview-charts").then((mod) => mod.RequestTrendChart), { ssr: false });
const ModelUsageChart = dynamic(() => import("../components/overview-charts").then((mod) => mod.ModelUsageChart), { ssr: false });
const ActiveUsersChart = dynamic(() => import("../components/overview-charts").then((mod) => mod.ActiveUsersChart), { ssr: false });
import { adminOverviewStatsAtom } from "@/atoms/admin/admin-query.atoms";

export default function AdminOverviewPage() {
  const { data: stats, isLoading } = useAtomValue(adminOverviewStatsAtom);

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Overview</h2>
        <p className="text-neutral-400 mt-2">Monitor system performance and key metrics.</p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {/* Total Users */}
        <Card className="bg-neutral-900 border-neutral-800">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-neutral-400">Total Users</CardTitle>
            <Users className="h-4 w-4 text-neutral-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-white">
              {stats?.total_users?.toLocaleString() || "0"}
            </div>
            <p className="text-xs text-green-500 flex items-center mt-1">
              <ArrowUpRight className="w-3 h-3 mr-1" /> +{stats?.today_users || "0"} today
            </p>
          </CardContent>
        </Card>

        {/* Total Requests */}
        <Card className="bg-neutral-900 border-neutral-800">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-neutral-400">Total Requests</CardTitle>
            <Activity className="h-4 w-4 text-neutral-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-white">
              {stats?.total_requests?.toLocaleString() || "0"}
            </div>
            <p className="text-xs text-green-500 flex items-center mt-1">
              <ArrowUpRight className="w-3 h-3 mr-1" /> +{stats?.today_requests?.toLocaleString() || "0"} today
            </p>
          </CardContent>
        </Card>

        {/* Total Conversations */}
        <Card className="bg-neutral-900 border-neutral-800">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-neutral-400">Conversations</CardTitle>
            <MessageSquare className="h-4 w-4 text-neutral-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-white">
              {stats?.total_conversations?.toLocaleString() || "0"}
            </div>
            <p className="text-xs text-neutral-500 mt-1">
              {stats?.active_conversations || "0"} active today
            </p>
          </CardContent>
        </Card>

        {/* Average Response Time */}
        <Card className="bg-neutral-900 border-neutral-800">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-neutral-400">Avg Response Time</CardTitle>
            <Zap className="h-4 w-4 text-neutral-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-white">{stats?.avg_response_time || "0"}s</div>
            <p className="text-xs text-green-400 flex items-center mt-1">
              <ArrowDownRight className="w-3 h-3 mr-1" /> Mocked Data
            </p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
        <Card className="lg:col-span-4 bg-neutral-900 border-neutral-800">
          <CardHeader>
            <CardTitle className="text-white">Request Trend</CardTitle>
          </CardHeader>
          <CardContent className="h-[300px]">
            <RequestTrendChart />
          </CardContent>
        </Card>
        
        <Card className="lg:col-span-3 bg-neutral-900 border-neutral-800">
          <CardHeader>
            <CardTitle className="text-white">Model Usage</CardTitle>
          </CardHeader>
          <CardContent className="h-[300px]">
            <ModelUsageChart />
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-1 lg:grid-cols-2">
        <Card className="bg-neutral-900 border-neutral-800">
          <CardHeader>
            <CardTitle className="text-white">Active Users (Today)</CardTitle>
          </CardHeader>
          <CardContent className="h-[300px]">
            <ActiveUsersChart />
          </CardContent>
        </Card>
        <Card className="bg-neutral-900 border-neutral-800">
          <CardHeader>
            <CardTitle className="text-white">Success Rate</CardTitle>
          </CardHeader>
          <CardContent className="h-[300px] flex items-center justify-center">
            <div className="text-center">
              <div className="text-6xl font-bold text-green-500 mb-2">{stats?.success_rate || "0"}%</div>
              <p className="text-neutral-400">{stats?.error_rate || "0"}% Error Rate</p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
