using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Configuration;
using OneClickHost.Api.Data;
using OneClickHost.Api.DTOs.Services;
using OneClickHost.Api.Models;

namespace OneClickHost.Api.Services;

public class ServiceService
{
    private readonly AppDbContext _db;
    private readonly IConfiguration _configuration;

    public ServiceService(AppDbContext db, IConfiguration configuration)
    {
        _db = db;
        _configuration = configuration;
    }

    public async Task<List<ServiceResponse>> GetServicesAsync(Guid projectId, Guid userId)
    {
        // Verify project ownership
        var projectExists = await _db.Projects.AnyAsync(p => p.Id == projectId && p.UserId == userId);
        if (!projectExists) throw new KeyNotFoundException("Project not found.");

        return await _db.Services
            .Where(s => s.ProjectId == projectId)
            .OrderByDescending(s => s.UpdatedAt)
            .Select(s => new ServiceResponse(
                s.Id, s.ProjectId, s.Name, s.RepoUrl, s.Branch,
                s.Subfolder, s.ServiceType, s.DetectedStack,
                s.Status, s.LiveUrl, s.CreatedAt, s.UpdatedAt))
            .ToListAsync();
    }

    public async Task<ServiceDetailResponse> GetServiceAsync(Guid serviceId, Guid userId)
    {
        var service = await _db.Services
            .Include(s => s.Project)
            .Include(s => s.EnvironmentVariables)
            .Include(s => s.Deployments.OrderByDescending(d => d.CreatedAt).Take(10))
            .FirstOrDefaultAsync(s => s.Id == serviceId && s.Project.UserId == userId)
            ?? throw new KeyNotFoundException("Service not found.");

        return new ServiceDetailResponse(
            service.Id, service.ProjectId, service.Name,
            service.RepoUrl, service.Branch, service.Subfolder,
            service.ServiceType, service.DetectedStack,
            service.ContainerId, service.Status, service.LiveUrl,
            service.EnvironmentVariables.Select(ev => new EnvVarResponse(
                ev.Id, ev.Key,
                ev.IsSecret ? "••••••••" : ev.Value,
                ev.IsSecret
            )).ToList(),
            service.Deployments.Select(d => new DeploymentSummary(
                d.Id, d.Status, d.Version,
                d.StartedAt, d.CompletedAt, d.CreatedAt
            )).ToList(),
            service.CreatedAt, service.UpdatedAt
        );
    }

    public async Task<ServiceResponse> CreateServiceAsync(Guid projectId, Guid userId, CreateServiceRequest request)
    {
        var projectExists = await _db.Projects.AnyAsync(p => p.Id == projectId && p.UserId == userId);
        if (!projectExists) throw new KeyNotFoundException("Project not found.");

        ValidateRepoUrl(request.RepoUrl);
        ValidateRelativeSubfolder(request.Subfolder);
        await EnforceServiceLimitAsync(userId);

        var service = new Service
        {
            ProjectId = projectId,
            Name = request.Name,
            RepoUrl = request.RepoUrl,
            Branch = request.Branch ?? "main",
            Subfolder = request.Subfolder,
            ServiceType = request.ServiceType ?? "frontend"
        };

        _db.Services.Add(service);
        await _db.SaveChangesAsync();

        return new ServiceResponse(
            service.Id, service.ProjectId, service.Name,
            service.RepoUrl, service.Branch, service.Subfolder,
            service.ServiceType, service.DetectedStack,
            service.Status, service.LiveUrl,
            service.CreatedAt, service.UpdatedAt);
    }

    public async Task<ServiceResponse> UpdateServiceAsync(Guid serviceId, Guid userId, UpdateServiceRequest request)
    {
        var service = await _db.Services
            .Include(s => s.Project)
            .FirstOrDefaultAsync(s => s.Id == serviceId && s.Project.UserId == userId)
            ?? throw new KeyNotFoundException("Service not found.");

        if (request.Name is not null) service.Name = request.Name;
        if (request.RepoUrl is not null)
        {
            ValidateRepoUrl(request.RepoUrl);
            service.RepoUrl = request.RepoUrl;
        }
        if (request.Branch is not null) service.Branch = request.Branch;
        if (request.Subfolder is not null)
        {
            ValidateRelativeSubfolder(request.Subfolder);
            service.Subfolder = request.Subfolder;
        }
        if (request.ServiceType is not null) service.ServiceType = request.ServiceType;

        service.UpdatedAt = DateTime.UtcNow;
        await _db.SaveChangesAsync();

        return new ServiceResponse(
            service.Id, service.ProjectId, service.Name,
            service.RepoUrl, service.Branch, service.Subfolder,
            service.ServiceType, service.DetectedStack,
            service.Status, service.LiveUrl,
            service.CreatedAt, service.UpdatedAt);
    }

    public async Task DeleteServiceAsync(Guid serviceId, Guid userId)
    {
        var service = await _db.Services
            .Include(s => s.Project)
            .FirstOrDefaultAsync(s => s.Id == serviceId && s.Project.UserId == userId)
            ?? throw new KeyNotFoundException("Service not found.");

        _db.Services.Remove(service);
        await _db.SaveChangesAsync();
    }

    public async Task UpdateEnvVarsAsync(Guid serviceId, Guid userId, List<EnvVarUpdateRequest> envVars)
    {
        var service = await _db.Services
            .Include(s => s.Project)
            .Include(s => s.EnvironmentVariables)
            .FirstOrDefaultAsync(s => s.Id == serviceId && s.Project.UserId == userId)
            ?? throw new KeyNotFoundException("Service not found.");

        // Remove old env vars and replace with new set
        _db.EnvironmentVariables.RemoveRange(service.EnvironmentVariables);

        foreach (var ev in envVars)
        {
            _db.EnvironmentVariables.Add(new EnvironmentVariable
            {
                ServiceId = serviceId,
                Key = ev.Key,
                Value = ev.Value,
                IsSecret = ev.IsSecret
            });
        }

        service.UpdatedAt = DateTime.UtcNow;
        await _db.SaveChangesAsync();
    }

    public async Task<List<EnvVarResponse>> GetEnvVarsAsync(Guid serviceId, Guid userId)
    {
        var service = await _db.Services
            .Include(s => s.Project)
            .Include(s => s.EnvironmentVariables)
            .FirstOrDefaultAsync(s => s.Id == serviceId && s.Project.UserId == userId)
            ?? throw new KeyNotFoundException("Service not found.");

        return service.EnvironmentVariables.Select(ev => new EnvVarResponse(
            ev.Id, ev.Key,
            ev.IsSecret ? "••••••••" : ev.Value,
            ev.IsSecret
        )).ToList();
    }

    private async Task EnforceServiceLimitAsync(Guid userId)
    {
        var limit = _configuration.GetValue("AntiAbuse:MaxActiveServicesPerUser", 20);
        var activeServices = await _db.Services
            .CountAsync(s => s.Project.UserId == userId);
        if (activeServices >= limit)
        {
            throw new InvalidOperationException($"Maximum active service limit reached ({limit}).");
        }
    }

    private static void ValidateRepoUrl(string repoUrl)
    {
        if (!Uri.TryCreate(repoUrl, UriKind.Absolute, out var uri) ||
            uri.Scheme != Uri.UriSchemeHttps ||
            !string.Equals(uri.Host, "github.com", StringComparison.OrdinalIgnoreCase) ||
            !string.IsNullOrEmpty(uri.UserInfo) ||
            !string.IsNullOrEmpty(uri.Query) ||
            !string.IsNullOrEmpty(uri.Fragment))
        {
            throw new ArgumentException("Repository URL must be a public https://github.com/owner/repo URL.");
        }

        var path = uri.AbsolutePath.Trim('/');
        if (path.EndsWith(".git", StringComparison.OrdinalIgnoreCase))
        {
            path = path[..^4];
        }
        var parts = path.Split('/', StringSplitOptions.RemoveEmptyEntries);
        if (parts.Length != 2 || parts.Any(p => p == "." || p == ".." || p.StartsWith('.')))
        {
            throw new ArgumentException("Repository URL must be a public https://github.com/owner/repo URL.");
        }
    }

    private static void ValidateRelativeSubfolder(string? subfolder)
    {
        if (string.IsNullOrWhiteSpace(subfolder)) return;
        if (Path.IsPathRooted(subfolder) ||
            subfolder.Split('/', '\\').Any(part => part is ".."))
        {
            throw new ArgumentException("Subfolder must be a relative path inside the repository.");
        }
    }
}
