using System.Security.Claims;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using OneClickHost.Api.DTOs.Projects;
using OneClickHost.Api.Services;

namespace OneClickHost.Api.Controllers;

[ApiController]
[Route("api/[controller]")]
[Authorize]
public class ProjectsController : ControllerBase
{
    private readonly ProjectService _projectService;

    public ProjectsController(ProjectService projectService)
    {
        _projectService = projectService;
    }

    [HttpGet]
    public async Task<ActionResult<List<ProjectResponse>>> GetProjects()
    {
        var userId = GetUserId();
        var projects = await _projectService.GetUserProjectsAsync(userId);
        return Ok(projects);
    }

    [HttpPost]
    public async Task<ActionResult<ProjectResponse>> CreateProject([FromBody] CreateProjectRequest request)
    {
        var userId = GetUserId();
        var project = await _projectService.CreateProjectAsync(userId, request);
        return CreatedAtAction(nameof(GetProject), new { id = project.Id }, project);
    }

    [HttpGet("{id:guid}")]
    public async Task<ActionResult<ProjectDetailResponse>> GetProject(Guid id)
    {
        try
        {
            var userId = GetUserId();
            var project = await _projectService.GetProjectAsync(id, userId);
            return Ok(project);
        }
        catch (KeyNotFoundException)
        {
            return NotFound(new { message = "Project not found." });
        }
    }

    [HttpDelete("{id:guid}")]
    public async Task<IActionResult> DeleteProject(Guid id)
    {
        try
        {
            var userId = GetUserId();
            await _projectService.DeleteProjectAsync(id, userId);
            return NoContent();
        }
        catch (KeyNotFoundException)
        {
            return NotFound(new { message = "Project not found." });
        }
    }

    private Guid GetUserId()
    {
        var claim = User.FindFirst(ClaimTypes.NameIdentifier)?.Value
            ?? throw new UnauthorizedAccessException();
        return Guid.Parse(claim);
    }
}
