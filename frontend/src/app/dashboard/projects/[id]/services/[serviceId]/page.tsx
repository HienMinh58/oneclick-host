"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Separator } from "@/components/ui/separator";

const statusColors: Record<string, string> = {
  created: "bg-gray-500/10 text-gray-400 border-gray-500/20",
  deploying: "bg-amber-500/10 text-amber-400 border-amber-500/20 animate-pulse",
  live: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  stopped: "bg-gray-500/10 text-gray-400 border-gray-500/20",
  failed: "bg-red-500/10 text-red-400 border-red-500/20",
  queued: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  cloning: "bg-amber-500/10 text-amber-400 border-amber-500/20 animate-pulse",
  building: "bg-amber-500/10 text-amber-400 border-amber-500/20 animate-pulse",
};

type ServiceData = Awaited<ReturnType<typeof api.getService>>;

export default function ServiceDetailPage() {
  const params = useParams();
  const serviceId = params.serviceId as string;
  const projectId = params.id as string;

  const [service, setService] = useState<ServiceData | null>(null);
  const [loading, setLoading] = useState(true);
  const [logs, setLogs] = useState<string | null>(null);
  const [logsDeploymentId, setLogsDeploymentId] = useState<string | null>(null);

  const loadService = useCallback(() => {
    api.getService(serviceId).then(setService).catch(console.error).finally(() => setLoading(false));
  }, [serviceId]);

  useEffect(() => { loadService(); }, [loadService]);

  const handleDeploy = async () => {
    try { await api.triggerDeploy(serviceId); loadService(); } catch (err) { console.error(err); }
  };

  const viewLogs = async (deploymentId: string) => {
    try {
      const data = await api.getDeploymentLogs(deploymentId);
      setLogs(data.buildLogs);
      setLogsDeploymentId(deploymentId);
    } catch (err) { console.error(err); }
  };

  if (loading) return <div className="flex items-center justify-center py-20"><div className="w-8 h-8 border-2 border-violet-500 border-t-transparent rounded-full animate-spin" /></div>;
  if (!service) return <div className="text-center py-20"><p className="text-muted-foreground">Service not found</p></div>;

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Link href="/dashboard/projects" className="hover:text-violet-400">Projects</Link>
        <span>/</span>
        <Link href={`/dashboard/projects/${projectId}`} className="hover:text-violet-400">Project</Link>
        <span>/</span>
        <span className="text-foreground">{service.name}</span>
      </div>

      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight">{service.name}</h1>
            <Badge className={statusColors[service.status] || ""}>{service.status}</Badge>
          </div>
          <p className="text-muted-foreground mt-1">{service.serviceType} · {service.detectedStack || "Stack not detected"} · {service.branch}</p>
          {service.liveUrl && (
            <a href={service.liveUrl} target="_blank" rel="noopener noreferrer" className="text-sm text-violet-400 hover:text-violet-300 mt-1 inline-block">
              🔗 {service.liveUrl}
            </a>
          )}
        </div>
        <Button onClick={handleDeploy} disabled={service.status === "deploying"} className="bg-gradient-to-r from-violet-600 to-indigo-600">
          {service.status === "deploying" ? "Deploying..." : "🚀 Deploy"}
        </Button>
      </div>

      <Separator />

      {/* Tabs */}
      <Tabs defaultValue="deployments" className="space-y-4">
        <TabsList><TabsTrigger value="deployments">Deployments</TabsTrigger><TabsTrigger value="env">Environment</TabsTrigger><TabsTrigger value="settings">Settings</TabsTrigger></TabsList>

        {/* Deployments Tab */}
        <TabsContent value="deployments" className="space-y-4">
          {service.recentDeployments.length === 0 ? (
            <Card className="border-border/50 border-dashed"><CardContent className="py-12 text-center text-muted-foreground">No deployments yet. Click Deploy to start.</CardContent></Card>
          ) : (
            <div className="space-y-3">
              {service.recentDeployments.map((d) => (
                <Card key={d.id} className="border-border/50">
                  <CardContent className="flex items-center justify-between py-4">
                    <div className="flex items-center gap-4">
                      <span className="text-sm font-mono text-muted-foreground">v{d.version}</span>
                      <Badge className={statusColors[d.status] || ""}>{d.status}</Badge>
                      <span className="text-sm text-muted-foreground">{new Date(d.createdAt).toLocaleString()}</span>
                    </div>
                    <Button variant="outline" size="sm" onClick={() => viewLogs(d.id)}>View Logs</Button>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}

          {/* Logs Panel */}
          {logs !== null && (
            <Card className="border-border/50">
              <CardHeader className="flex flex-row items-center justify-between py-3">
                <CardTitle className="text-sm font-mono">Build Logs — {logsDeploymentId?.slice(0, 8)}</CardTitle>
                <Button variant="ghost" size="sm" onClick={() => { setLogs(null); setLogsDeploymentId(null); }}>Close</Button>
              </CardHeader>
              <CardContent><pre className="text-xs font-mono bg-black/50 rounded-lg p-4 max-h-96 overflow-auto whitespace-pre-wrap">{logs || "No logs available"}</pre></CardContent>
            </Card>
          )}
        </TabsContent>

        {/* Environment Tab */}
        <TabsContent value="env">
          <Card className="border-border/50">
            <CardHeader><CardTitle className="text-lg">Environment Variables</CardTitle></CardHeader>
            <CardContent>
              {service.environmentVariables.length === 0 ? (
                <p className="text-muted-foreground text-sm">No environment variables configured.</p>
              ) : (
                <div className="space-y-2">
                  {service.environmentVariables.map((ev) => (
                    <div key={ev.id} className="flex items-center gap-4 font-mono text-sm">
                      <span className="text-violet-400">{ev.key}</span><span className="text-muted-foreground">=</span><span>{ev.isSecret ? "••••••••" : ev.value}</span>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Settings Tab */}
        <TabsContent value="settings">
          <Card className="border-border/50">
            <CardHeader><CardTitle className="text-lg">Service Info</CardTitle></CardHeader>
            <CardContent className="space-y-3 text-sm">
              <div className="flex justify-between"><span className="text-muted-foreground">Repository</span><a href={service.repoUrl} target="_blank" className="text-violet-400">{service.repoUrl}</a></div>
              <div className="flex justify-between"><span className="text-muted-foreground">Branch</span><span>{service.branch}</span></div>
              {service.subfolder && <div className="flex justify-between"><span className="text-muted-foreground">Subfolder</span><span>{service.subfolder}</span></div>}
              {service.containerId && <div className="flex justify-between"><span className="text-muted-foreground">Container ID</span><span className="font-mono">{service.containerId}</span></div>}
              <div className="flex justify-between"><span className="text-muted-foreground">Created</span><span>{new Date(service.createdAt).toLocaleString()}</span></div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
