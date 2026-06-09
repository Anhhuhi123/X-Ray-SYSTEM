"use client";

import { useState } from "react";
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
import { Search, Eye, ArrowRight, FileText, Bot, MessageCircle } from "lucide-react";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Separator } from "@/components/ui/separator";
import { ScrollArea } from "@/components/ui/scroll-area";

const mockRAGRequests = [
  { id: "req_111", timestamp: "2026-06-09 11:00:01", user: "Alice Nguyen", question: "How to deploy NFD?", retrievedDocs: 5, avgScore: 0.92, model: "GPT-4o", time: "2.3s", status: "Success",
    details: {
      originalQuery: "How to deploy NFD?",
      rewrittenQuery: "deployment guide instructions NFD docker compose server setup",
      docs: [
        { name: "deployment_guide.md", chunkId: "chk_01", source: "Documentation", score: 0.95, text: "To deploy NFD, use the docker-compose file located in the /docker directory..." },
        { name: "system_architecture.md", chunkId: "chk_02", source: "Documentation", score: 0.89, text: "The NFD architecture is composed of a FastAPI backend and a Next.js frontend, deployed via..." }
      ],
      systemPrompt: "You are a helpful AI assistant. Answer the question based on the context provided.",
      finalAnswer: "To deploy NFD, you should use the `docker-compose` file located in the `/docker` directory. It will spin up both the FastAPI backend and Next.js frontend."
    }
  },
  { id: "req_222", timestamp: "2026-06-09 10:55:12", user: "Bob Tran", question: "What is ElectricSQL?", retrievedDocs: 2, avgScore: 0.85, model: "Claude 3.5", time: "1.8s", status: "Success",
    details: {
      originalQuery: "What is ElectricSQL?",
      rewrittenQuery: "ElectricSQL definition realtime sync local-first database postgres",
      docs: [
        { name: "electric_sql_overview.pdf", chunkId: "chk_09", source: "External", score: 0.85, text: "ElectricSQL is a local-first sync layer that provides active-active database synchronization..." }
      ],
      systemPrompt: "You are a helpful AI assistant. Answer the question based on the context provided.",
      finalAnswer: "ElectricSQL is a local-first sync layer that enables active-active database synchronization, allowing real-time capabilities for your frontend applications."
    }
  },
  { id: "req_333", timestamp: "2026-06-09 10:40:00", user: "Charlie Le", question: "Explain the flux capacitor", retrievedDocs: 0, avgScore: 0.0, model: "Gemini 1.5", time: "0.5s", status: "Miss",
    details: {
      originalQuery: "Explain the flux capacitor",
      rewrittenQuery: "flux capacitor explanation mechanism",
      docs: [],
      systemPrompt: "You are a helpful AI assistant. Answer the question based on the context provided.",
      finalAnswer: "I'm sorry, but I couldn't find any information about a 'flux capacitor' in the provided knowledge base."
    }
  }
];

export default function RAGObservabilityPage() {
  const [selectedReq, setSelectedReq] = useState<typeof mockRAGRequests[0] | null>(null);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight text-white">RAG Observability</h2>
        <p className="text-neutral-400 mt-2">Monitor the entire Retrieval-Augmented Generation pipeline.</p>
      </div>

      <Card className="bg-neutral-900 border-neutral-800">
        <CardHeader className="pb-4 border-b border-neutral-800">
          <div className="flex items-center justify-between">
            <CardTitle className="text-white">RAG Requests</CardTitle>
            <div className="relative w-64">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-neutral-500" />
              <Input 
                placeholder="Search queries..." 
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
                <TableHead className="text-neutral-400 text-right">Docs</TableHead>
                <TableHead className="text-neutral-400 text-right">Avg Score</TableHead>
                <TableHead className="text-neutral-400 text-right">Time</TableHead>
                <TableHead className="text-neutral-400 text-right">Status</TableHead>
                <TableHead className="text-neutral-400 text-right">Action</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {mockRAGRequests.map((req) => (
                <TableRow key={req.id} className="border-neutral-800 hover:bg-neutral-800/50">
                  <TableCell className="text-neutral-400 whitespace-nowrap">{req.timestamp}</TableCell>
                  <TableCell className="font-medium text-white">{req.user}</TableCell>
                  <TableCell className="text-neutral-300 max-w-[250px] truncate">{req.question}</TableCell>
                  <TableCell className="text-right text-neutral-300">{req.retrievedDocs}</TableCell>
                  <TableCell className="text-right text-neutral-300">
                    <Badge variant="secondary" className="bg-neutral-800 text-neutral-300">{req.avgScore}</Badge>
                  </TableCell>
                  <TableCell className="text-right text-neutral-400">{req.time}</TableCell>
                  <TableCell className="text-right">
                    <Badge variant="outline" className={
                      req.status === "Success" ? "border-green-500/30 text-green-500" : "border-yellow-500/30 text-yellow-500"
                    }>
                      {req.status}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    <button 
                      onClick={() => setSelectedReq(req)}
                      className="p-2 text-neutral-400 hover:text-white hover:bg-neutral-800 rounded-md transition-colors"
                    >
                      <Eye className="w-4 h-4" />
                    </button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Sheet open={!!selectedReq} onOpenChange={(open) => !open && setSelectedReq(null)}>
        <SheetContent className="bg-neutral-950 border-neutral-800 text-white w-[600px] sm:max-w-2xl p-0 flex flex-col">
          <SheetHeader className="p-6 border-b border-neutral-800">
            <SheetTitle className="text-white">RAG Pipeline Trace</SheetTitle>
            <SheetDescription className="text-neutral-400">
              Request ID: {selectedReq?.id}
            </SheetDescription>
          </SheetHeader>

          <ScrollArea className="flex-1 p-6">
            {selectedReq && (
              <div className="space-y-8 relative">
                {/* Pipeline visual line */}
                <div className="absolute left-6 top-8 bottom-8 w-px bg-neutral-800 z-0"></div>

                {/* 1. Original Question */}
                <div className="relative z-10 flex gap-4">
                  <div className="w-12 h-12 rounded-full bg-blue-500/10 border border-blue-500/30 flex items-center justify-center shrink-0">
                    <MessageCircle className="w-5 h-5 text-blue-500" />
                  </div>
                  <div className="flex-1 space-y-2">
                    <h4 className="text-sm font-medium text-blue-400">1. Original Question</h4>
                    <div className="bg-neutral-900 border border-neutral-800 rounded-md p-3 text-white text-sm">
                      {selectedReq.details.originalQuery}
                    </div>
                  </div>
                </div>

                {/* 2. Query Rewrite */}
                <div className="relative z-10 flex gap-4">
                  <div className="w-12 h-12 rounded-full bg-purple-500/10 border border-purple-500/30 flex items-center justify-center shrink-0">
                    <ArrowRight className="w-5 h-5 text-purple-500" />
                  </div>
                  <div className="flex-1 space-y-2">
                    <h4 className="text-sm font-medium text-purple-400">2. Query Rewrite & Keywords</h4>
                    <div className="bg-neutral-900 border border-neutral-800 rounded-md p-3 text-neutral-300 text-sm font-mono text-xs">
                      {selectedReq.details.rewrittenQuery}
                    </div>
                  </div>
                </div>

                {/* 3. Retrieved Context */}
                <div className="relative z-10 flex gap-4">
                  <div className="w-12 h-12 rounded-full bg-orange-500/10 border border-orange-500/30 flex items-center justify-center shrink-0">
                    <FileText className="w-5 h-5 text-orange-500" />
                  </div>
                  <div className="flex-1 space-y-2">
                    <h4 className="text-sm font-medium text-orange-400">3. Retrieved Context ({selectedReq.retrievedDocs} docs)</h4>
                    {selectedReq.details.docs.length > 0 ? (
                      <div className="space-y-3">
                        {selectedReq.details.docs.map((doc, idx) => (
                          <div key={idx} className="bg-neutral-900 border border-neutral-800 rounded-md p-3">
                            <div className="flex items-center justify-between mb-2">
                              <span className="text-xs font-medium text-white">{doc.name}</span>
                              <Badge variant="secondary" className="bg-neutral-800 text-neutral-400 text-[10px]">Score: {doc.score}</Badge>
                            </div>
                            <p className="text-xs text-neutral-400 italic line-clamp-3">{doc.text}</p>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="bg-neutral-900 border border-neutral-800 rounded-md p-3 text-neutral-500 text-sm italic">
                        No context retrieved.
                      </div>
                    )}
                  </div>
                </div>

                {/* 4. Final Answer */}
                <div className="relative z-10 flex gap-4">
                  <div className="w-12 h-12 rounded-full bg-green-500/10 border border-green-500/30 flex items-center justify-center shrink-0">
                    <Bot className="w-5 h-5 text-green-500" />
                  </div>
                  <div className="flex-1 space-y-2">
                    <h4 className="text-sm font-medium text-green-400">4. Final Generated Answer</h4>
                    <div className="bg-neutral-900 border border-neutral-800 rounded-md p-3 text-white text-sm">
                      {selectedReq.details.finalAnswer}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </ScrollArea>
        </SheetContent>
      </Sheet>
    </div>
  );
}
