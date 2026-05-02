namespace OneClickHost.Api.DTOs.Deployments;

public record DeploymentResponse(
    Guid Id,
    Guid ServiceId,
    string Status,
    string? ImageTag,
    string? ErrorMessage,
    int Version,
    DateTime? StartedAt,
    DateTime? CompletedAt,
    DateTime CreatedAt
);

public record DeploymentLogsResponse(
    Guid DeploymentId,
    string Status,
    string? BuildLogs
);
