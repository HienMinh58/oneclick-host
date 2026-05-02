using System.ComponentModel.DataAnnotations;

namespace OneClickHost.Api.DTOs.Auth;

public record RegisterRequest(
    [Required, EmailAddress] string Email,
    [Required, MinLength(6)] string Password,
    [Required, MaxLength(100)] string FullName
);

public record LoginRequest(
    [Required, EmailAddress] string Email,
    [Required] string Password
);

public record AuthResponse(
    Guid Id,
    string Email,
    string FullName,
    string Token
);

public record UserProfileResponse(
    Guid Id,
    string Email,
    string FullName,
    DateTime CreatedAt
);
