# OneClick-Host AWS Dev EC2

This Terraform stack creates the EC2-only MVP environment:

- One Ubuntu EC2 instance, default `t3.medium`
- One Elastic IP
- Security group with public HTTP, admin SSH, and optional admin-only Traefik dashboard port
- Docker, Docker Compose, and the OneClick-Host stack bootstrapped with cloud-init
- PostgreSQL runs as the existing Compose `db` container, not RDS
- No purchased domain is required by default. When `domain_name = ""`, the stack uses `<public-ip>.sslip.io` for wildcard DNS.

## Usage

1. Copy the example variables:

   ```bash
   cp terraform.tfvars.example terraform.tfvars
   ```

2. Edit `terraform.tfvars`:

   - `key_name`
   - `admin_cidr_blocks`
   - `repository_url` and `repository_ref`
   - `postgres_password`, `jwt_secret`, `oneclick_secret_key`
   - Optional: `domain_name`, only if you own a domain

3. Apply:

   ```bash
   terraform init
   terraform fmt
   terraform validate
   terraform plan
   terraform apply
   ```

4. If `domain_name = ""`, no DNS setup is needed. Open the Terraform `app_url` output, for example:

   ```text
   http://13.250.10.20.sslip.io
   ```

   User apps will also work as subdomains, for example:

   ```text
   http://frontend-demo.13.250.10.20.sslip.io
   ```

5. If you set a real `domain_name`, point DNS to the Terraform `public_ip` output:

   ```text
   A  example.com   -> <public_ip>
   A  *.example.com -> <public_ip>
   ```

6. Open:

   ```text
   terraform output app_url
   ```

## EC2 Operations

SSH:

```bash
ssh -i <path-to-private-key> ubuntu@<public_ip>
```

Check services:

```bash
cd /opt/oneclick-host
docker compose -f docker-compose.yml -f docker-compose.ec2.yml ps
docker logs oneclick-api
```

Restart:

```bash
cd /opt/oneclick-host
sudo systemctl restart oneclick-host
```

Inspect bootstrap or service logs:

```bash
sudo tail -200 /var/log/oneclick-bootstrap.log
sudo journalctl -u oneclick-host -n 200 --no-pager
```

## Notes

- Public traffic should enter through Traefik on port `80`.
- The EC2 override removes direct host exposure for Postgres, API, and frontend.
- The Traefik dashboard port is disabled at the security group by default.
- HTTPS can be added later by opening `443` and adding an ACME resolver in Traefik.
- The generated `.env` values are rendered through EC2 user data, so keep Terraform state private.
- `sslip.io` is convenient for dev/test. For production, switch `domain_name` to a real domain.
