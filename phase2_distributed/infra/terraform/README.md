# Phase 2 Infrastructure (Terraform Blueprints)

These `.tf` files are **illustrative blueprints** matching SDD Phase 2,
Section 4 (AWS Architecture) and Section 21 (Deployment Architecture) —
they show the intended shape of the AWS deployment (VPC/networking, ECS
Fargate services, scheduled Lambda jobs) using valid Terraform syntax.

They are **not** meant to be run with `terraform apply` as-is. Before
using them for a real deployment you'll need to, at minimum:

- Fill in a real `backend` block (S3 + DynamoDB state locking)
- Set your AWS account ID / ECR image URIs in `ecs/main.tf`
- Provide real VPC CIDR ranges / region in `networking/main.tf`
- Point `cockroachdb/main.tf` at a real CockroachDB Cloud cluster (via the
  CockroachDB Terraform provider) or a self-hosted multi-region setup
- Package `phase2_distributed/memory_tiering/retier_job.py` as a proper
  Lambda deployment artifact for `lambda/main.tf`

## Folder mapping to the SDD

| Folder         | SDD Section | Covers |
|----------------|-------------|--------|
| `networking/`  | 4.1         | VPC, public/private subnets |
| `ecs/`         | 4.1, 21     | ECS Fargate cluster + task/service defs for the 5 microservices |
| `cockroachdb/` | 5, 19       | Multi-region cluster config placeholders (REGIONAL/GLOBAL locality) |
| `lambda/`      | 4.1, 12.2   | Scheduled jobs: memory re-tiering / CDC export |
