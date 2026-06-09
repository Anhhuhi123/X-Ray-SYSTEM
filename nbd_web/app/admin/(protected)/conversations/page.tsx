"use client";

import { useState, useMemo } from "react";
import { 
  Table, 
  TableBody, 
  TableCell, 
  TableHead, 
  TableHeader, 
  TableRow 
} from "@/components/ui/table";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Search, Eye, Clock, Database, Cpu, MessageSquare } from "lucide-react";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Separator } from "@/components/ui/separator";

import { useAtomValue } from "jotai";
import { adminConversationsQueryAtom } from "@/atoms/admin/admin-query.atoms";
import { useDebouncedValue } from "@/hooks/use-debounced-value";
import type { AdminConversationItem } from "@/lib/apis/admin-api.service";

export default function AdminConversationsPage() {
  const [selectedConv, setSelectedConv] = useState<AdminConversationItem | null>(null);
  
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebouncedValue(search, 500);

  const queryAtom = useMemo(() => adminConversationsQueryAtom(page, pageSize, debouncedSearch), [page, pageSize, debouncedSearch]);
  const { data, isLoading } = useAtomValue(queryAtom);

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearch(e.target.value);
    setPage(1); // Reset to first page on search
  };

  const handleNextPage = () => {
    if (data && page * pageSize < data.total) {
      setPage(page + 1);
    }
  };

  const handlePrevPage = () => {
    if (page > 1) {
      setPage(page - 1);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight text-white">Conversation Tracking</h2>
        <p className="text-neutral-400 mt-2">Monitor all chat histories and LLM interactions.</p>
      </div>

      <Card className="bg-neutral-900 border-neutral-800">
        <CardHeader className="pb-4 border-b border-neutral-800">
          <div className="flex items-center justify-between">
            <CardTitle className="text-white">Recent Conversations</CardTitle>
            <div className="relative w-64">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-neutral-500" />
              <Input 
                placeholder="Search queries..." 
                value={search}
                onChange={handleSearchChange}
                className="pl-9 bg-neutral-950 border-neutral-800 text-white placeholder:text-neutral-500"
              />
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader className="bg-neutral-950 border-b border-neutral-800">
              <TableRow className="hover:bg-transparent border-neutral-800">
                <TableHead className="text-neutral-400">Timestamp</TableHead>
                <TableHead className="text-neutral-400">User</TableHead>
                <TableHead className="text-neutral-400">Question</TableHead>
                <TableHead className="text-neutral-400 hidden lg:table-cell">Answer Preview</TableHead>
                <TableHead className="text-neutral-400">Model</TableHead>
                <TableHead className="text-neutral-400 text-right">Time</TableHead>
                <TableHead className="text-neutral-400 text-right">Status</TableHead>
                <TableHead className="text-neutral-400 text-right">Action</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                <TableRow>
                  <TableCell colSpan={8} className="text-center py-8">
                    <Loader2 className="h-6 w-6 animate-spin text-blue-500 mx-auto" />
                  </TableCell>
                </TableRow>
              ) : data?.items.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={8} className="text-center py-8 text-neutral-500">
                    No conversations found
                  </TableCell>
                </TableRow>
              ) : (
                data?.items.map((conv) => (
                  <TableRow key={conv.id} className="border-neutral-800 hover:bg-neutral-800/50">
                    <TableCell className="text-neutral-400 whitespace-nowrap">
                      {new Date(conv.timestamp).toLocaleString()}
                    </TableCell>
                    <TableCell className="font-medium text-white">{conv.user}</TableCell>
                    <TableCell className="text-neutral-300 max-w-[200px] truncate">{conv.question}</TableCell>
                    <TableCell className="text-neutral-400 hidden lg:table-cell max-w-[250px] truncate">{conv.answerPreview}</TableCell>
                    <TableCell className="text-neutral-300">
                      <span className="flex items-center">
                        <Cpu className="w-3 h-3 mr-1 text-neutral-500" />
                        {conv.model}
                      </span>
                    </TableCell>
                    <TableCell className="text-right text-neutral-400">{conv.responseTime}</TableCell>
                    <TableCell className="text-right">
                      <Badge variant="outline" className={
                        conv.status === "Success" 
                          ? "border-green-500/30 text-green-500" 
                          : conv.status === "Empty"
                          ? "border-neutral-500/30 text-neutral-500"
                          : "border-red-500/30 text-red-500"
                      }>
                        {conv.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      <button 
                        onClick={() => setSelectedConv(conv)}
                        className="p-2 text-neutral-400 hover:text-white hover:bg-neutral-800 rounded-md transition-colors"
                      >
                        <Eye className="w-4 h-4" />
                      </button>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
          
          <div className="p-4 border-t border-neutral-800 flex items-center justify-between text-sm text-neutral-400">
            <div>
              Showing {data?.total ? Math.min((page - 1) * pageSize + 1, data.total) : 0} to{" "}
              {data?.total ? Math.min(page * pageSize, data.total) : 0} of {data?.total || 0} conversations
            </div>
            <div className="flex items-center gap-2">
              <button 
                onClick={handlePrevPage} 
                disabled={page <= 1}
                className="px-3 py-1 border border-neutral-800 rounded hover:bg-neutral-800 disabled:opacity-50"
              >
                Previous
              </button>
              <button 
                onClick={handleNextPage} 
                disabled={!data || page * pageSize >= data.total}
                className="px-3 py-1 border border-neutral-800 rounded hover:bg-neutral-800 disabled:opacity-50"
              >
                Next
              </button>
            </div>
          </div>
        </CardContent>
      </Card>

      <Sheet open={!!selectedConv} onOpenChange={(open) => !open && setSelectedConv(null)}>
        <SheetContent className="bg-neutral-950 border-neutral-800 text-white w-[500px] sm:max-w-xl overflow-y-auto">
          <SheetHeader className="mb-6">
            <SheetTitle className="text-white">Conversation Details</SheetTitle>
            <SheetDescription className="text-neutral-400">
              ID: {selectedConv?.id}
            </SheetDescription>
          </SheetHeader>

          {selectedConv && (
            <div className="space-y-6">
              {/* Question */}
              <div>
                <h4 className="text-sm font-medium text-neutral-400 mb-2 flex items-center">
                  <MessageSquare className="w-4 h-4 mr-2" />
                  User Question
                </h4>
                <div className="bg-neutral-900 border border-neutral-800 rounded-md p-4 text-white text-sm">
                  {selectedConv.question}
                </div>
              </div>

              {/* Answer */}
              <div>
                <h4 className="text-sm font-medium text-neutral-400 mb-2 flex items-center">
                  <Cpu className="w-4 h-4 mr-2" />
                  AI Answer
                </h4>
                <div className="bg-neutral-900 border border-neutral-800 rounded-md p-4 text-neutral-200 text-sm whitespace-pre-wrap">
                  {selectedConv.fullAnswer}
                </div>
              </div>

              <Separator className="bg-neutral-800" />

              {/* Metadata */}
              <div>
                <h4 className="text-sm font-medium text-neutral-400 mb-4 flex items-center">
                  <Database className="w-4 h-4 mr-2" />
                  Metadata
                </h4>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div className="space-y-1">
                    <p className="text-neutral-500">Conversation ID</p>
                    <p className="text-white font-mono text-xs">{selectedConv.id}</p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-neutral-500">Message ID</p>
                    <p className="text-white font-mono text-xs">{selectedConv.messageId}</p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-neutral-500">User ID</p>
                    <p className="text-white font-mono text-xs">{selectedConv.userId}</p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-neutral-500">Timestamp</p>
                    <p className="text-white">{selectedConv.timestamp}</p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-neutral-500">Model</p>
                    <p className="text-white">{selectedConv.model}</p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-neutral-500">Response Time</p>
                    <p className="text-white flex items-center">
                      <Clock className="w-3 h-3 mr-1" />
                      {selectedConv.responseTime}
                    </p>
                  </div>
                  
                  {/* Tokens */}
                  <div className="col-span-2 mt-2 p-3 bg-neutral-900 rounded-md border border-neutral-800">
                    <p className="text-neutral-400 mb-2 font-medium">Token Usage</p>
                    <div className="flex justify-between items-center text-xs">
                      <div className="text-center">
                        <p className="text-neutral-500 mb-1">Input</p>
                        <p className="text-white font-mono">{selectedConv.tokens.input}</p>
                      </div>
                      <div className="text-neutral-600">+</div>
                      <div className="text-center">
                        <p className="text-neutral-500 mb-1">Output</p>
                        <p className="text-white font-mono">{selectedConv.tokens.output}</p>
                      </div>
                      <div className="text-neutral-600">=</div>
                      <div className="text-center">
                        <p className="text-neutral-500 mb-1">Total</p>
                        <p className="text-white font-mono font-bold text-blue-400">{selectedConv.tokens.total}</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </SheetContent>
      </Sheet>
    </div>
  );
}
