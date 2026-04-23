# Terraform — Fly.io Infrastructure

This directory declares the Fly.io app, dedicated IPs, and machine as Infrastructure as Code.

## One-time setup

1. Install Terraform (`brew install terraform`) and `flyctl` (`brew install flyctl`).
2. Run `fly auth login` and then `fly tokens create org` to get an API token.
3. Copy the token: `cp terraform.tfvars.example terraform.tfvars` and paste the token.

## Usage

```bash
cd terraform
terraform init                 # fetch the fly provider
terraform plan                 # preview changes
terraform apply                # create the app + IPs + machine
terraform output app_url       # print the public URL
```

To tear down everything:

```bash
terraform destroy
```

## What this manages

| Resource | Purpose |
|----------|---------|
| `fly_app.service` | Fly app shell (name + org) |
| `fly_ip.ipv4` / `fly_ip.ipv6` | Dedicated public IPs |
| `fly_machine.service` | The actual VM running the container |

## What this does NOT manage

- **Application secrets** (`AZURE_CLIENT_ID`, `GEMINI_API_KEY`, etc.) are set via
  `fly secrets set KEY=value` so they're never written to Terraform state.
- **Container image builds.** CircleCI builds and pushes the image; Terraform just
  points the machine at it.

## CI usage

CircleCI runs `flyctl deploy` (not `terraform apply`) for day-to-day pushes.
Terraform is invoked manually when the infrastructure shape itself changes
(e.g. region, memory, number of machines).
