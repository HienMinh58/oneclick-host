using Microsoft.EntityFrameworkCore;
using OneClickHost.Api.Data;
using OneClickHost.Api.DTOs.Projects;
using OneClickHost.Api.Models;

namespace OneClickHost.Api.Services;

public class ProjectService
{
    private readonly AppDbContext _db;

    public ProjectService(AppDbContext db)
    {
        _db = db;
    }

    public async Task<List<ProjectResponse>> GetUserProjectsAsync(Guid userId)
    {
        return await _db.Projects
            .Where(p => p.UserId == userId)
            .OrderByDescending(p => p.UpdatedAt)
            .Select(p => new ProjectResponse(
                p.Id, p.Name, p.Description,
                p.Services.Count,
                p.CreatedAt, p.UpdatedAt))
            .ToListAsync();
    }

    public async Task<ProjectDetailResponse> GetProjectAsync(Guid projectId, Guid userId)
    {
        var project = await _db.Projects
            .Include(p => p.Services)
            .FirstOrDefaultAsync(p => p.Id == projectId && p.UserId == userId)
            ?? throw new KeyNotFoundException("Project not found.");

        return new ProjectDetailResponse(
            project.Id, project.Name, project.Description,
            project.Services.Select(s => new ProjectServiceSummary(
                s.Id, s.Name, s.ServiceType, s.DetectedStack, s.Status, s.LiveUrl
            )).ToList(),
            project.CreatedAt, project.UpdatedAt
        );
    }

    public async Task<ProjectResponse> CreateProjectAsync(Guid userId, CreateProjectRequest request)
    {
        var project = new Project
        {
            UserId = userId,
            Name = request.Name,
            Description = request.Description
        };

        _db.Projects.Add(project);
        await _db.SaveChangesAsync();

        return new ProjectResponse(
            project.Id, project.Name, project.Description,
            0, project.CreatedAt, project.UpdatedAt);
    }

    public async Task DeleteProjectAsync(Guid projectId, Guid userId)
    {
        var project = await _db.Projects
            .FirstOrDefaultAsync(p => p.Id == projectId && p.UserId == userId)
            ?? throw new KeyNotFoundException("Project not found.");

        _db.Projects.Remove(project);
        await _db.SaveChangesAsync();
    }
}
