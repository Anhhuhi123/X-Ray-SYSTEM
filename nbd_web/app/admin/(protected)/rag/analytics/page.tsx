"use client";

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Search, Database, AlertCircle, TrendingUp } from "lucide-react";
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from "recharts";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

const scoreData = [
  { range: "0.0 - 0.2", count: 12 },
  { range: "0.2 - 0.4", count: 34 },
  { range: "0.4 - 0.6", count: 145 },
  { range: "0.6 - 0.8", count: 430 },
  { range: "0.8 - 1.0", count: 850 },
];

const knowledgeGaps = [
  { query: "How to configure custom SSO?", frequency: 142, avgScore: 0.12 },
  { query: "List of supported local models", frequency: 89, avgScore: 0.25 },
  { query: "API rate limits per tier", frequency: 56, avgScore: 0.05 },
  { query: "ElectricSQL migration guide", frequency: 41, avgScore: 0.31 },
];

export default function RAGAnalyticsPage() {
  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-3xl font-bold tracking-tight text-white">RAG Analytics</h2>
        <p className="text-neutral-400 mt-2">Analyze retrieval performance and identify knowledge gaps.</p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card className="bg-neutral-900 border-neutral-800">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-neutral-400">Total RAG Queries</CardTitle>
            <Search className="h-4 w-4 text-neutral-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-white">14,230</div>
            <p className="text-xs text-neutral-500 mt-1">This month</p>
          </CardContent>
        </Card>

        <Card className="bg-neutral-900 border-neutral-800">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-neutral-400">Avg Retrieval Score</CardTitle>
            <TrendingUp className="h-4 w-4 text-neutral-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-500">0.82</div>
            <p className="text-xs text-neutral-500 mt-1">Target &gt; 0.75</p>
          </CardContent>
        </Card>

        <Card className="bg-neutral-900 border-neutral-800">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-neutral-400">Failed Retrievals</CardTitle>
            <AlertCircle className="h-4 w-4 text-neutral-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-400">2.4%</div>
            <p className="text-xs text-neutral-500 mt-1">Score &lt; 0.3</p>
          </CardContent>
        </Card>

        <Card className="bg-neutral-900 border-neutral-800">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-neutral-400">Avg Docs Retrieved</CardTitle>
            <Database className="h-4 w-4 text-neutral-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-white">3.5</div>
            <p className="text-xs text-neutral-500 mt-1">Per query</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-2">
        <Card className="bg-neutral-900 border-neutral-800">
          <CardHeader>
            <CardTitle className="text-white">Retrieval Score Distribution</CardTitle>
            <CardDescription className="text-neutral-400">Histogram of semantic search scores</CardDescription>
          </CardHeader>
          <CardContent className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={scoreData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#262626" vertical={false} />
                <XAxis dataKey="range" stroke="#525252" fontSize={12} tickLine={false} axisLine={false} />
                <YAxis stroke="#525252" fontSize={12} tickLine={false} axisLine={false} />
                <Tooltip 
                  contentStyle={{ backgroundColor: "#171717", borderColor: "#262626", borderRadius: "8px", color: "#fff" }}
                  cursor={{ fill: '#262626' }}
                />
                <Bar dataKey="count" fill="#3b82f6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card className="bg-neutral-900 border-neutral-800">
          <CardHeader>
            <CardTitle className="text-white text-red-400">Knowledge Gaps</CardTitle>
            <CardDescription className="text-neutral-400">High frequency queries with low retrieval scores</CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader className="bg-neutral-950 border-b border-neutral-800">
                <TableRow className="hover:bg-transparent border-neutral-800">
                  <TableHead className="text-neutral-400">Query Pattern</TableHead>
                  <TableHead className="text-neutral-400 text-right">Frequency</TableHead>
                  <TableHead className="text-neutral-400 text-right">Avg Score</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {knowledgeGaps.map((gap, idx) => (
                  <TableRow key={idx} className="border-neutral-800 hover:bg-neutral-800/50">
                    <TableCell className="font-medium text-white">{gap.query}</TableCell>
                    <TableCell className="text-right text-neutral-300">{gap.frequency}</TableCell>
                    <TableCell className="text-right">
                      <span className="text-red-400 font-mono text-sm bg-red-500/10 px-2 py-1 rounded">
                        {gap.avgScore}
                      </span>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
