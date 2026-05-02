using System.Security.Claims;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using OneClickHost.Api.DTOs.Deployments;
using OneClickHost.Api.Services;

namespace OneClickHost.Api.Controllers;

[ApiController]
[Authorize]
public class DeploymentsController : ControllerBase
{
    private readonly DeploymentService _deploymentService;

    public DeploymentsController(DeploymentService deploymentService)
    {
        _deploymentService = deploymentService;
    }

    [HttpPost("api/services/{serviceId:guid}/deploy")]
    public async Task<ActionResult<DeploymentResponse>> TriggerDeployment(Guid serviceId)
    {
        try
        {
            var userId = GetUserId();
            var deployment = await _deploymentService.TriggerDeploymentAsync(serviceId, userId);
            return AcceptedAtAction(nameof(GetDeployment), new { id = deployment.Id }, deployment);
        }
        catch (KeyNotFoundException)
        {
            return NotFound(new { message = "Service not found." });
        }
    }

    [HttpGet("api/services/{serviceId:guid}/deployments")]
    public async Task<ActionResult<List<DeploymentResponse>>> GetDeployments(Guid serviceId)
    {
        try
        {
            var userId = GetUserId();
            var deployments = await _deploymentService.GetDeploymentsAsync(serviceId, userId);
            return Ok(deployments);
        }
        catch (KeyNotFoundException)
        {
            return NotFound(new { message = "Service not found." });
        }
    }

    [HttpGet("api/deployments/{id:guid}")]
    public async Task<ActionResult<DeploymentResponse>> GetDeployment(Guid id)
    {
        try
        {
            var userId = GetUserId();
            var deployment = await _deploymentService.GetDeploymentAsync(id, userId);
            return Ok(deployment);
        }
        catch (KeyNotFoundException)
        {
            return NotFound(new { message = "Deployment not found." });
        }
    }

    [HttpGet("api/deployments/{id:guid}/logs")]
    public async Task<ActionResult<DeploymentLogsResponse>> GetDeploymentLogs(Guid id)
    {
        try
        {
            var userId = GetUserId();
            var logs = await _deploymentService.GetDeploymentLogsAsync(id, userId);
            return Ok(logs);
        }
        catch (KeyNotFoundException)
        {
            return NotFound(new { message = "Deployment not found." });
        }
    }

    private Guid GetUserId()
    {
        var claim = User.FindFirst(ClaimTypes.NameIdentifier)?.Value
            ?? throw new UnauthorizedAccessException();
        return Guid.Parse(claim);
    }
}
