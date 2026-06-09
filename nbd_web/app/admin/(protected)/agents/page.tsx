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
import { Search, Eye, Cpu, Clock, Terminal, Github, FileCode, CheckCircle2 } from "lucide-react";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";

const mockAgentExecutions = [
  { id: "exec_11a", timestamp: "2026-06-09 11:30:15", user: "Alice Nguyen", request: "Create Login Page", agent: "Hermes 2.5", time: "14.2s", status: "Success",
    details: {
      userRequest: "Create a modern Next.js login page using TailwindCSS and Lucide React icons.",
      reasoning: "1. Understand the requirement: Next.js, TailwindCSS, Lucide React.\n2. Read existing layout or components to match style (MCP: filesystem.read).\n3. Generate the React component code.\n4. Write the file to /app/login/page.tsx (MCP: filesystem.write).\n5. Verify syntax and dependencies.",
      toolCalls: [
        { tool: "filesystem.read", args: { path: "components/ui/button.tsx" }, duration: "120ms", status: "Success", icon: FileCode },
        { tool: "filesystem.read", args: { path: "components/ui/input.tsx" }, duration: "105ms", status: "Success", icon: FileCode },
        { tool: "terminal.execute", args: { command: "npm install lucide-react" }, duration: "4.5s", status: "Success", icon: Terminal },
        { tool: "filesystem.write", args: { path: "app/login/page.tsx", content: "..." }, duration: "300ms", status: "Success", icon: FileCode },
        { tool: "git.commit", args: { message: "feat: add login page" }, duration: "1.2s", status: "Success", icon: Github },
      ],
      result: "Login page successfully created at /app/login/page.tsx and committed."
    }
  },
  { id: "exec_22b", timestamp: "2026-06-09 11:25:00", user: "Bob Tran", request: "Search web for latest FastAPI docs", agent: "Hermes 2.5", time: "8.5s", status: "Success",
    details: {
      userRequest: "Search the web for the latest FastAPI documentation regarding WebSockets.",
      reasoning: "1. Call browser.search tool to search for 'FastAPI WebSockets documentation'.\n2. Extract content from the top result.\n3. Summarize the findings for the user.",
      toolCalls: [
        { tool: "browser.search", args: { query: "FastAPI WebSockets documentation" }, duration: "3.2s", status: "Success", icon: Search },
        { tool: "browser.extract", args: { url: "https://fastapi.tiangolo.com/advanced/websockets/" }, duration: "2.1s", status: "Success", icon: FileCode },
      ],
      result: "Successfully retrieved and summarized FastAPI WebSockets documentation."
    }
  },
  { id: "exec_33c", timestamp: "2026-06-09 11:10:45", user: "Charlie Le", request: "Run database migration", agent: "Hermes 2.5", time: "5.1s", status: "Failed",
    details: {
      userRequest: "Run the alembic database migration to head.",
      reasoning: "1. Open terminal.\n2. Execute 'alembic upgrade head'.\n3. Return result.",
      toolCalls: [
        { tool: "terminal.execute", args: { command: "alembic upgrade head" }, duration: "2.4s", status: "Failed", icon: Terminal },
      ],
      result: "Failed to execute. Error: target database is not up to date. Please resolve conflicts."
    }
  }
];

export default function AgentExecutionPage() {
  const [selectedExec, setSelectedExec] = useState<typeof mockAgentExecutions[0] | null>(null);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight text-white">Agent Execution Monitoring</h2>
        <p className="text-neutral-400 mt-2">Track Deep Agent reasoning plans and MCP tool calls.</p>
      </div>

      <Card className="bg-neutral-900 border-neutral-800">
        <CardHeader className="pb-4 border-b border-neutral-800">
          <div className="flex items-center justify-between">
            <CardTitle className="text-white">Agent Requests</CardTitle>
            <div className="relative w-64">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-neutral-500" />
              <Input 
                placeholder="Search executions..." 
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
                <TableHead className="text-neutral-400">Request</TableHead>
                <TableHead className="text-neutral-400">Agent</TableHead>
                <TableHead className="text-neutral-400 text-right">Time</TableHead>
                <TableHead className="text-neutral-400 text-right">Status</TableHead>
                <TableHead className="text-neutral-400 text-right">Action</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {mockAgentExecutions.map((exec) => (
                <TableRow key={exec.id} className="border-neutral-800 hover:bg-neutral-800/50">
                  <TableCell className="text-neutral-400 whitespace-nowrap">{exec.timestamp}</TableCell>
                  <TableCell className="font-medium text-white">{exec.user}</TableCell>
                  <TableCell className="text-neutral-300 max-w-[250px] truncate">{exec.request}</TableCell>
                  <TableCell className="text-neutral-400">
                    <span className="flex items-center">
                      <Cpu className="w-3 h-3 mr-1 text-blue-500" />
                      {exec.agent}
                    </span>
                  </TableCell>
                  <TableCell className="text-right text-neutral-400">{exec.time}</TableCell>
                  <TableCell className="text-right">
                    <Badge variant="outline" className={
                      exec.status === "Success" ? "border-green-500/30 text-green-500" : "border-red-500/30 text-red-500"
                    }>
                      {exec.status}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    <button 
                      onClick={() => setSelectedExec(exec)}
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

      <Sheet open={!!selectedExec} onOpenChange={(open) => !open && setSelectedExec(null)}>
        <SheetContent className="bg-neutral-950 border-neutral-800 text-white w-[600px] sm:max-w-2xl p-0 flex flex-col">
          <SheetHeader className="p-6 border-b border-neutral-800">
            <SheetTitle className="text-white flex items-center justify-between">
              <span>Execution Trace</span>
              <Badge className={selectedExec?.status === "Success" ? "bg-green-500/20 text-green-400" : "bg-red-500/20 text-red-400"}>
                {selectedExec?.time}
              </Badge>
            </SheetTitle>
            <SheetDescription className="text-neutral-400">
              ID: {selectedExec?.id}
            </SheetDescription>
          </SheetHeader>

          <ScrollArea className="flex-1 p-6">
            {selectedExec && (
              <div className="space-y-6">
                {/* Request */}
                <div className="space-y-2">
                  <h4 className="text-sm font-medium text-neutral-400 flex items-center">
                    User Request
                  </h4>
                  <div className="bg-neutral-900 border border-neutral-800 rounded-md p-3 text-white text-sm">
                    {selectedExec.details.userRequest}
                  </div>
                </div>

                {/* Reasoning */}
                <div className="space-y-2">
                  <h4 className="text-sm font-medium text-neutral-400 flex items-center">
                    Hermes Reasoning Plan
                  </h4>
                  <div className="bg-[#1e1e1e] border border-neutral-800 rounded-md p-3 text-green-400 font-mono text-sm whitespace-pre-wrap">
                    {selectedExec.details.reasoning}
                  </div>
                </div>

                <Separator className="bg-neutral-800" />

                {/* Timeline */}
                <div className="space-y-4">
                  <h4 className="text-sm font-medium text-neutral-400 flex items-center">
                    Tool Calls Timeline
                  </h4>
                  <div className="space-y-3 relative before:absolute before:inset-0 before:ml-5 before:-translate-x-px md:before:mx-auto md:before:translate-x-0 before:h-full before:w-0.5 before:bg-gradient-to-b before:from-transparent before:via-neutral-800 before:to-transparent">
                    {selectedExec.details.toolCalls.map((tool, idx) => (
                      <div key={idx} className="relative flex items-center justify-between md:justify-normal md:odd:flex-row-reverse group is-active">
                        <div className="flex items-center justify-center w-10 h-10 rounded-full border border-neutral-800 bg-neutral-900 text-neutral-500 group-[.is-active]:text-blue-500 group-[.is-active]:bg-blue-500/10 shadow shrink-0 md:order-1 md:group-odd:-translate-x-1/2 md:group-even:translate-x-1/2 z-10">
                          <tool.icon className="w-4 h-4" />
                        </div>
                        <div className="w-[calc(100%-4rem)] md:w-[calc(50%-2.5rem)] bg-neutral-900 border border-neutral-800 p-3 rounded-md shadow flex flex-col">
                          <div className="flex items-center justify-between mb-1">
                            <span className="font-mono text-xs text-blue-400 font-medium">{tool.tool}</span>
                            <span className="text-xs text-neutral-500">{tool.duration}</span>
                          </div>
                          <div className="text-xs text-neutral-400 font-mono line-clamp-1">
                            {JSON.stringify(tool.args)}
                          </div>
                          <div className="mt-2 flex justify-end">
                            <Badge variant="outline" className={tool.status === "Success" ? "border-green-500/30 text-green-500 text-[10px]" : "border-red-500/30 text-red-500 text-[10px]"}>
                              {tool.status}
                            </Badge>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <Separator className="bg-neutral-800" />

                {/* Result */}
                <div className="space-y-2 pb-8">
                  <h4 className="text-sm font-medium text-neutral-400 flex items-center">
                    Execution Result
                  </h4>
                  <div className={`border rounded-md p-3 text-sm flex items-start ${selectedExec.status === "Success" ? "bg-green-500/10 border-green-500/20 text-green-400" : "bg-red-500/10 border-red-500/20 text-red-400"}`}>
                    <CheckCircle2 className="w-5 h-5 mr-2 shrink-0" />
                    <span>{selectedExec.details.result}</span>
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
