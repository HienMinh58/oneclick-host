using System.ComponentModel.DataAnnotations;

namespace OneClickHost.Api.DTOs.Projects;

public record CreateProjectRequest(
    [Required, MaxLength(100)] string Name,
    [MaxLength(500)] string? Description
);

public record ProjectResponse(
    Guid Id,
    string Name,
    string? Description,
    int ServiceCount,
    DateTime CreatedAt,
    DateTime UpdatedAt
);

public record ProjectDetailResponse(
    Guid Id,
    string Name,
    string? Description,
    List<ProjectServiceSummary> Services,
    DateTime CreatedAt,
    DateTime UpdatedAt
);

public record ProjectServiceSummary(
    Guid Id,
    string Name,
    string ServiceType,
    string? DetectedStack,
    string Status,
    string? LiveUrl
);
