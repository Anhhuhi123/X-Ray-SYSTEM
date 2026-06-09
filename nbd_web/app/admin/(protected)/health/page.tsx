import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Activity, Server, Database, BrainCircuit, Cpu, Layers } from "lucide-react";

export default function SystemHealthPage() {
  const coreServices = [
    { name: "aos-ai Gateway", status: "Operational", uptime: "99.9%", latency: "45ms", icon: Server },
    { name: "Hermes Agent Engine", status: "Operational", uptime: "99.8%", latency: "120ms", icon: Cpu },
    { name: "RAG Service", status: "Operational", uptime: "99.9%", latency: "210ms", icon: Layers },
    { name: "MCP Gateway", status: "Degraded", uptime: "98.5%", latency: "850ms", icon: Activity },
  ];

  const databases = [
    { name: "Primary Database (PostgreSQL)", status: "Operational", storage: "45% used", icon: Database },
    { name: "Vector Database (pgvector)", status: "Operational", storage: "62% used", icon: Database },
    { name: "Redis Cache & Broker", status: "Operational", storage: "12% used", icon: Database },
  ];

  const llmProviders = [
    { name: "OpenAI (GPT-4o)", status: "Operational", latency: "600ms", icon: BrainCircuit },
    { name: "Anthropic (Claude 3.5)", status: "Operational", latency: "850ms", icon: BrainCircuit },
    { name: "Google (Gemini 1.5)", status: "Operational", latency: "720ms", icon: BrainCircuit },
    { name: "Local Model (Llama 3)", status: "Offline", latency: "-", icon: BrainCircuit },
  ];

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-3xl font-bold tracking-tight text-white flex items-center">
          System Health
          <Badge className="ml-4 bg-green-500/20 text-green-400 hover:bg-green-500/20">All Systems Operational</Badge>
        </h2>
        <p className="text-neutral-400 mt-2">Real-time status of AirenoOS infrastructure and external providers.</p>
      </div>

      <div className="space-y-4">
        <h3 className="text-lg font-medium text-white">Core Services</h3>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {coreServices.map((service) => (
            <Card key={service.name} className="bg-neutral-900 border-neutral-800">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium text-neutral-400">{service.name}</CardTitle>
                <service.icon className="h-4 w-4 text-neutral-500" />
              </CardHeader>
              <CardContent>
                <div className="flex items-center justify-between mt-2">
                  <div className="flex items-center">
                    <div className={`w-2 h-2 rounded-full mr-2 ${service.status === "Operational" ? "bg-green-500" : "bg-yellow-500"}`}></div>
                    <span className="text-sm font-medium text-white">{service.status}</span>
                  </div>
                  <span className="text-xs text-neutral-500">{service.latency}</span>
                </div>
                <div className="mt-4 text-xs text-neutral-500 flex justify-between border-t border-neutral-800 pt-3">
                  <span>Uptime (30d)</span>
                  <span className="text-white">{service.uptime}</span>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>

      <div className="space-y-4">
        <h3 className="text-lg font-medium text-white">Databases & Storage</h3>
        <div className="grid gap-4 md:grid-cols-3">
          {databases.map((db) => (
            <Card key={db.name} className="bg-neutral-900 border-neutral-800">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium text-neutral-400">{db.name}</CardTitle>
                <db.icon className="h-4 w-4 text-neutral-500" />
              </CardHeader>
              <CardContent>
                <div className="flex items-center justify-between mt-2">
                  <div className="flex items-center">
                    <div className="w-2 h-2 rounded-full bg-green-500 mr-2"></div>
                    <span className="text-sm font-medium text-white">{db.status}</span>
                  </div>
                </div>
                <div className="mt-4 text-xs text-neutral-500 flex justify-between border-t border-neutral-800 pt-3">
                  <span>Storage</span>
                  <span className="text-white">{db.storage}</span>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>

      <div className="space-y-4">
        <h3 className="text-lg font-medium text-white">LLM Providers</h3>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {llmProviders.map((llm) => (
            <Card key={llm.name} className="bg-neutral-900 border-neutral-800">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium text-neutral-400">{llm.name}</CardTitle>
                <llm.icon className="h-4 w-4 text-neutral-500" />
              </CardHeader>
              <CardContent>
                <div className="flex items-center justify-between mt-2">
                  <div className="flex items-center">
                    <div className={`w-2 h-2 rounded-full mr-2 ${llm.status === "Operational" ? "bg-green-500" : "bg-red-500"}`}></div>
                    <span className="text-sm font-medium text-white">{llm.status}</span>
                  </div>
                </div>
                <div className="mt-4 text-xs text-neutral-500 flex justify-between border-t border-neutral-800 pt-3">
                  <span>Latency</span>
                  <span className="text-white">{llm.latency}</span>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}
