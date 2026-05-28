import { ExternalLink, Loader2, Network, ServerCog } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { api, type ComposeService, type ProjectDetail } from "@/lib/api";

const typeLabel: Record<string, string> = {
  service: "Service",
  database: "Database",
  cache: "Cache",
  worker: "Worker",
  reverse_proxy: "Reverse proxy",
};

export function ComposeServicesPanel({ project, projectId }: { project: ProjectDetail; projectId: string }) {
  const [services, setServices] = useState<ComposeService[]>([]);
  const [loading, setLoading] = useState(Boolean(project.composeConfig?.repoUrl));
  const [error, setError] = useState<string | null>(null);

  const loadServices = useCallback(() => {
    if (!project.composeConfig?.repoUrl) {
      setServices([]);
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);
    api
      .getComposeServices(projectId)
      .then(setServices)
      .catch((err) => setError(err instanceof Error ? err.message : "Could not load Compose services"))
      .finally(() => setLoading(false));
  }, [project.composeConfig?.repoUrl, projectId]);

  useEffect(() => {
    loadServices();
  }, [loadServices, project.updatedAt]);

  if (!project.composeConfig?.repoUrl) {
    return (
      <Card className="border-dashed">
        <CardContent className="flex flex-col items-center justify-center gap-4 py-16 text-center">
          <ServerCog className="h-10 w-10 text-muted-foreground" />
          <div>
            <p className="font-medium">No Compose services yet</p>
            <p className="mt-1 text-sm text-muted-foreground">Save a Compose config to view stack services here.</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (loading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center gap-3 py-16 text-sm text-muted-foreground">
          <Loader2 className="h-5 w-5 animate-spin" />
          Loading Compose services...
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="border-dashed">
        <CardContent className="flex flex-col items-center justify-center gap-4 py-16 text-center">
          <ServerCog className="h-10 w-10 text-muted-foreground" />
          <div>
            <p className="font-medium">Compose services unavailable</p>
            <p className="mt-1 max-w-xl text-sm text-muted-foreground">{error}</p>
          </div>
          <Button variant="outline" onClick={loadServices}>
            Retry
          </Button>
        </CardContent>
      </Card>
    );
  }

  if (services.length === 0) {
    return (
      <Card className="border-dashed">
        <CardContent className="flex flex-col items-center justify-center gap-4 py-16 text-center">
          <ServerCog className="h-10 w-10 text-muted-foreground" />
          <div>
            <p className="font-medium">No services found</p>
            <p className="mt-1 text-sm text-muted-foreground">The saved Compose source did not return any services.</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border bg-card px-4 py-3">
        <div>
          <p className="text-sm font-medium">Compose services</p>
          <p className="text-xs text-muted-foreground">Read-only services from the saved Docker Compose stack.</p>
        </div>
        <Badge variant="outline">{services.length} services</Badge>
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        {services.map((service) => {
          const routeLiveUrls = service.routes
            .map((route) => route.liveUrl)
            .filter((url): url is string => Boolean(url));
          const liveUrls = routeLiveUrls.length > 0
            ? routeLiveUrls
            : services.length === 1
              ? project.composeConfig?.liveUrls ?? []
              : [];
          const isPublic = service.isPublic || liveUrls.length > 0;

          return (
            <Card key={service.name} className="transition-colors hover:border-primary/40">
              <CardHeader>
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <CardTitle className="truncate text-base">{service.name}</CardTitle>
                    <CardDescription className="mt-1 flex flex-wrap gap-2">
                      <Badge variant="secondary">{typeLabel[service.type] ?? service.type}</Badge>
                      <Badge variant={isPublic ? "default" : "outline"}>{isPublic ? "Public" : "Private"}</Badge>
                      <Badge variant="outline">{service.status}</Badge>
                    </CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-4 text-sm">
                <div className="space-y-1">
                  <MetaLine label="Image" value={service.image} />
                  <MetaLine label="Build" value={service.buildContext} />
                  <MetaLine label="Ports" value={service.ports.length ? service.ports.join(", ") : null} />
                </div>

                <LiveUrlSection urls={liveUrls} />

                {service.routes.length > 0 && (
                  <div className="space-y-2">
                    <p className="text-xs font-semibold uppercase text-muted-foreground">Routes</p>
                    <div className="space-y-1">
                      {service.routes.map((route) => (
                        <div key={`${route.routeSlug}:${route.internalPort}`} className="flex min-w-0 items-center justify-between gap-2 rounded-md bg-muted/45 px-2 py-1.5">
                          <span className="truncate">
                            {route.routeSlug} {"->"} {route.internalPort}
                          </span>
                          {route.liveUrl && (
                            <a href={route.liveUrl} className="inline-flex shrink-0 items-center gap-1 text-primary" target="_blank" rel="noreferrer">
                              <ExternalLink className="h-3.5 w-3.5" />
                              Open
                            </a>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <ChipGroup label="Depends on" values={service.dependencies} />
                <ChipGroup label="Env" values={service.environmentKeys} />
                <ChipGroup label="Volumes" values={service.volumes} />
                <div className="flex min-w-0 items-center gap-2 text-xs text-muted-foreground">
                  <Network className="h-3.5 w-3.5 shrink-0" />
                  <span className="truncate">{service.networks.length ? service.networks.join(", ") : "default network"}</span>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}

function LiveUrlSection({ urls }: { urls: string[] }) {
  return (
    <div className="space-y-2 rounded-md border bg-muted/30 px-3 py-2.5">
      <p className="text-xs font-semibold uppercase text-muted-foreground">Live URL</p>
      {urls.length > 0 ? (
        <div className="space-y-1">
          {urls.map((url) => (
            <a key={url} href={url} className="inline-flex max-w-full items-center gap-1 truncate text-primary" target="_blank" rel="noreferrer">
              <span className="truncate">{url}</span>
              <ExternalLink className="h-3.5 w-3.5 shrink-0" />
            </a>
          ))}
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">Live URL not available yet</p>
      )}
    </div>
  );
}

function MetaLine({ label, value }: { label: string; value: string | null }) {
  if (!value) return null;
  return (
    <div className="flex min-w-0 justify-between gap-3">
      <span className="shrink-0 text-muted-foreground">{label}</span>
      <span className="truncate font-medium">{value}</span>
    </div>
  );
}

function ChipGroup({ label, values }: { label: string; values: string[] }) {
  if (values.length === 0) return null;
  return (
    <div className="space-y-2">
      <p className="text-xs font-semibold uppercase text-muted-foreground">{label}</p>
      <div className="flex flex-wrap gap-1.5">
        {values.map((value) => (
          <Badge key={value} variant="outline" className="max-w-full truncate">
            {value}
          </Badge>
        ))}
      </div>
    </div>
  );
}
