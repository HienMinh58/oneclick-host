"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";

const statusColors: Record<string, string> = {
  created: "bg-gray-500/10 text-gray-400 border-gray-500/20",
  deploying: "bg-amber-500/10 text-amber-400 border-amber-500/20 animate-pulse",
  live: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  stopped: "bg-gray-500/10 text-gray-400 border-gray-500/20",
  failed: "bg-red-500/10 text-red-400 border-red-500/20",
};

export default function ProjectDetailPage() {
  const params = useParams();
  const projectId = params.id as string;
  const [project, setProject] = useState<{ id: string; name: string; description: string | null; services: { id: string; name: string; serviceType: string; detectedStack: string | null; status: string; liveUrl: string | null }[]; createdAt: string } | null>(null);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [svcName, setSvcName] = useState("");
  const [repoUrl, setRepoUrl] = useState("");
  const [branch, setBranch] = useState("main");
  const [subfolder, setSubfolder] = useState("");
  const [serviceType, setServiceType] = useState("frontend");
  const [creating, setCreating] = useState(false);

  const loadProject = () => { api.getProject(projectId).then(setProject).catch(console.error).finally(() => setLoading(false)); };
  useEffect(() => { loadProject(); }, [projectId]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleCreateService = async (e: React.FormEvent) => {
    e.preventDefault(); setCreating(true);
    try { await api.createService(projectId, { name: svcName, repoUrl, branch: branch || undefined, subfolder: subfolder || undefined, serviceType }); setSvcName(""); setRepoUrl(""); setBranch("main"); setSubfolder(""); setDialogOpen(false); loadProject(); } catch (err) { console.error(err); } finally { setCreating(false); }
  };

  const handleDeploy = async (serviceId: string) => { try { await api.triggerDeploy(serviceId); loadProject(); } catch (err) { console.error(err); } };

  if (loading) return <div className="flex items-center justify-center py-20"><div className="w-8 h-8 border-2 border-violet-500 border-t-transparent rounded-full animate-spin" /></div>;
  if (!project) return <div className="text-center py-20"><p className="text-muted-foreground">Project not found</p></div>;

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
            <Link href="/dashboard/projects" className="hover:text-violet-400 transition-colors">Projects</Link>
            <span>/</span><span className="text-foreground">{project.name}</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight">{project.name}</h1>
          {project.description && <p className="text-muted-foreground mt-1">{project.description}</p>}
        </div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger className="inline-flex items-center justify-center rounded-md text-sm font-medium px-4 py-2 bg-gradient-to-r from-violet-600 to-indigo-600 text-white cursor-pointer">+ Add Service</DialogTrigger>
          <DialogContent>
            <DialogHeader><DialogTitle>Add Service</DialogTitle><DialogDescription>Connect a GitHub repository</DialogDescription></DialogHeader>
            <form onSubmit={handleCreateService} className="space-y-4 mt-4">
              <div className="space-y-2"><Label>Service Name</Label><Input placeholder="frontend" value={svcName} onChange={(e) => setSvcName(e.target.value)} required /></div>
              <div className="space-y-2"><Label>GitHub Repository URL</Label><Input placeholder="https://github.com/user/repo" value={repoUrl} onChange={(e) => setRepoUrl(e.target.value)} required /></div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2"><Label>Branch</Label><Input placeholder="main" value={branch} onChange={(e) => setBranch(e.target.value)} /></div>
                <div className="space-y-2"><Label>Subfolder</Label><Input placeholder="apps/web" value={subfolder} onChange={(e) => setSubfolder(e.target.value)} /></div>
              </div>
              <div className="space-y-2"><Label>Type</Label><div className="flex gap-2">{["frontend","backend"].map(t=><Button key={t} type="button" variant={serviceType===t?"default":"outline"} size="sm" onClick={()=>setServiceType(t)} className={serviceType===t?"bg-violet-600":""}>{t}</Button>)}</div></div>
              <div className="flex justify-end gap-2"><Button type="button" variant="outline" onClick={()=>setDialogOpen(false)}>Cancel</Button><Button type="submit" disabled={creating} className="bg-gradient-to-r from-violet-600 to-indigo-600">{creating?"Adding...":"Add Service"}</Button></div>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {project.services.length === 0 ? (
        <Card className="border-border/50 border-dashed"><CardContent className="flex flex-col items-center justify-center py-16 space-y-4"><div className="w-16 h-16 rounded-2xl bg-violet-500/10 flex items-center justify-center text-3xl">🔗</div><div className="text-center"><p className="font-medium">No services yet</p><p className="text-sm text-muted-foreground mt-1">Add a service to connect your GitHub repo</p></div></CardContent></Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {project.services.map((svc) => (
            <Card key={svc.id} className="border-border/50 hover:border-violet-500/30 transition-colors">
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div><Link href={`/dashboard/projects/${projectId}/services/${svc.id}`}><CardTitle className="text-lg hover:text-violet-400 transition-colors cursor-pointer">{svc.name}</CardTitle></Link><CardDescription className="mt-1">{svc.serviceType} · {svc.detectedStack||"not detected"}</CardDescription></div>
                  <Badge className={statusColors[svc.status]||""}>{svc.status}</Badge>
                </div>
              </CardHeader>
              <CardContent>
                <div className="flex items-center justify-between">
                  {svc.liveUrl ? <a href={svc.liveUrl} target="_blank" rel="noopener noreferrer" className="text-sm text-violet-400 hover:text-violet-300 truncate">{svc.liveUrl}</a> : <span className="text-sm text-muted-foreground">Not deployed</span>}
                  <Button size="sm" onClick={()=>handleDeploy(svc.id)} disabled={svc.status==="deploying"} className="bg-gradient-to-r from-violet-600 to-indigo-600 ml-2">{svc.status==="deploying"?"Deploying...":"Deploy"}</Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
