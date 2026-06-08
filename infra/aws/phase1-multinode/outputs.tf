output "control_plane_public_ip" {
  description = "Only public IPv4 used by phase one."
  value       = aws_eip.control_plane.public_ip
}

output "control_plane_private_ip" {
  description = "Private API/NAT IP for execution-node traffic."
  value       = aws_network_interface.control_plane.private_ip
}

output "execution_node_private_ip" {
  description = "Private-only execution-node IP."
  value       = aws_network_interface.execution_node.private_ip
}

output "app_url" {
  description = "Dashboard URL through sslip.io."
  value       = "http://${local.domain_name}"
}

output "effective_domain" {
  description = "Base domain used by public app routes."
  value       = local.domain_name
}

output "control_plane_ssh_command" {
  description = "SSH command for the public control-plane node."
  value       = "ssh -i <path-to-private-key> ubuntu@${aws_eip.control_plane.public_ip}"
}

output "execution_node_ssh_command" {
  description = "SSH command to reach the private execution-node through the control-plane bastion."
  value       = "ssh -i <path-to-private-key> -J ubuntu@${aws_eip.control_plane.public_ip} ubuntu@${aws_network_interface.execution_node.private_ip}"
}

output "fixture_repo" {
  description = "Public Compose fixture repo for acceptance testing."
  value       = "https://github.com/tuankiet18-dev/oneclick-compose-fixture"
}

output "cost_note" {
  description = "Cost-oriented shape of this stack."
  value       = "No NAT Gateway, no ALB, no RDS, one public IPv4. Control-plane acts as a small NAT instance for the private execution-node."
}
