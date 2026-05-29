using OneClickHost.Api.DTOs.Projects;
using OneClickHost.Api.Services;

var tests = new (string Name, Action Test)[]
{
    ("parses core compose resources", ParsesCoreComposeResources),
    ("classifies infrastructure services", ClassifiesInfrastructureServices),
    ("maps compose services for services tab", MapsComposeServicesForServicesTab),
    ("returns empty graph for compose without services", ReturnsEmptyGraphForMissingServices),
};

foreach (var test in tests)
{
    test.Test();
    Console.WriteLine($"PASS {test.Name}");
}

static void ParsesCoreComposeResources()
{
    const string yaml = """
services:
  web:
    build: ./web
    ports:
      - "8080:80"
    environment:
      API_URL: http://api:8000
      SECRET_TOKEN: keep-me-private
    depends_on:
      api:
        condition: service_started
    volumes:
      - web-cache:/app/cache:rw
    networks:
      - public
  api:
    image: ghcr.io/example/api:latest
    environment:
      DATABASE_URL: postgres://db:5432/app
    depends_on:
      - db
  db:
    image: postgres:16-alpine
volumes:
  web-cache:
networks:
  public:
""";

    var graph = DeploymentGraphParser.Parse(yaml);

    AssertContainsNode(graph.Nodes, "service:web", "service");
    AssertContainsNode(graph.Nodes, "service:api", "service");
    AssertContainsNode(graph.Nodes, "service:db", "database");
    AssertContainsNode(graph.Nodes, "env:web:API_URL", "env_var");
    AssertContainsNode(graph.Nodes, "volume:web-cache", "volume");
    AssertContainsNode(graph.Nodes, "network:public", "network");
    AssertContainsEdge(graph.Edges, "depends_on", "service:web", "service:api");
    AssertContainsEdge(graph.Edges, "depends_on", "service:api", "service:db");
    AssertContainsEdge(graph.Edges, "uses_env", "service:web", "env:web:API_URL");
    AssertContainsEdge(graph.Edges, "mounts", "service:web", "volume:web-cache");
    AssertContainsEdge(graph.Edges, "exposes", "service:web", "network:public");
    AssertContainsEdge(graph.Edges, "connects_to", "service:web", "service:api");
}

static void ClassifiesInfrastructureServices()
{
    const string yaml = """
services:
  db:
    image: postgres:16-alpine
  redis:
    image: redis:7-alpine
  worker:
    image: example/app
    command: celery worker
  traefik:
    image: traefik:v3.4
""";

    var graph = DeploymentGraphParser.Parse(yaml);

    AssertContainsNode(graph.Nodes, "service:db", "database");
    AssertContainsNode(graph.Nodes, "service:redis", "cache");
    AssertContainsNode(graph.Nodes, "service:worker", "worker");
    AssertContainsNode(graph.Nodes, "service:traefik", "reverse_proxy");
}

static void MapsComposeServicesForServicesTab()
{
    const string yaml = """
services:
  frontend:
    build: ./frontend
    ports:
      - "8080:80"
    environment:
      API_URL: http://api:8000
    depends_on:
      - api
  api:
    image: ghcr.io/example/api:latest
    environment:
      DATABASE_URL: postgres://db:5432/app
    depends_on:
      - db
      - redis
  db:
    image: postgres:16-alpine
    volumes:
      - pgdata:/var/lib/postgresql/data
  redis:
    image: redis:7-alpine
volumes:
  pgdata:
""";

    var services = ComposeServiceListParser.Parse(
        yaml,
        [
            new ComposeRouteResponse("frontend", "app", 80, "traefik", "/", "https://app.example.test"),
            new ComposeRouteResponse("api", "api", 8000, "traefik", "/health", "https://api.example.test")
        ],
        [new ComposeEnvVarResponse("api", "JWT_SECRET", "********", true)],
        "live");

    var frontend = services.Single(service => service.Name == "frontend");
    var apiService = services.Single(service => service.Name == "api");
    var db = services.Single(service => service.Name == "db");
    var redis = services.Single(service => service.Name == "redis");

    AssertEqual("service", frontend.Type, "frontend type");
    AssertContains(frontend.Ports, 80, "frontend ports");
    AssertContains(frontend.Dependencies, "api", "frontend dependencies");
    AssertEqual(true, frontend.IsPublic, "frontend public flag");
    AssertEqual("live", frontend.Status, "frontend status");
    AssertContains(apiService.EnvironmentKeys, "JWT_SECRET", "api env keys");
    AssertEqual("database", db.Type, "db type");
    AssertContains(db.Volumes, "pgdata:/var/lib/postgresql/data", "db volumes");
    AssertEqual("cache", redis.Type, "redis type");
}

static void AssertContains<T>(IEnumerable<T> values, T expected, string name)
{
    if (!values.Contains(expected))
        throw new Exception($"Expected {name} to contain {expected}.");
}

static void ReturnsEmptyGraphForMissingServices()
{
    const string yaml = """
name: no-services
volumes:
  data:
""";

    var graph = DeploymentGraphParser.Parse(yaml);
    AssertEqual(0, graph.Nodes.Count, "node count");
    AssertEqual(0, graph.Edges.Count, "edge count");
}

static void AssertContainsNode(IEnumerable<DeploymentGraphNodeResponse> nodes, string id, string type)
{
    if (!nodes.Any(node => node.Id == id && node.Type == type))
        throw new Exception($"Expected node {id} with type {type}.");
}

static void AssertContainsEdge(IEnumerable<DeploymentGraphEdgeResponse> edges, string type, string source, string target)
{
    if (!edges.Any(edge => edge.Type == type && edge.Source == source && edge.Target == target))
        throw new Exception($"Expected edge {type}: {source} -> {target}.");
}

static void AssertEqual<T>(T expected, T actual, string name)
{
    if (!EqualityComparer<T>.Default.Equals(expected, actual))
        throw new Exception($"Expected {name} to be {expected}, got {actual}.");
}
