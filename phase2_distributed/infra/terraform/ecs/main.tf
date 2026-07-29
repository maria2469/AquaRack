# ECS Fargate blueprint running the 5 Phase 2 microservices (SDD Section
# 4.1: "ECS Fargate / EKS — Runs the FastAPI microservices (Telemetry,
# Digital Twin, Water Model, Agent, Dashboard API)"). Illustrative only —
# see ../README.md before applying.

variable "aws_account_id" {
  description = "Fill in before applying"
  default     = "ACCOUNT_ID"
}

variable "aws_region" {
  default = "us-east-1"
}

variable "services" {
  description = "Matches phase2_distributed/services/*"
  default = [
    "telemetry-service",
    "digital-twin-service",
    "water-model-service",
    "agent-service",
    "dashboard-api-service",
  ]
}

resource "aws_ecs_cluster" "aquamind" {
  name = "aquamind-ai-phase2"
}

resource "aws_ecs_task_definition" "service" {
  for_each                 = toset(var.services)
  family                   = "aquamind-${each.value}"
  requires_compatibilities  = ["FARGATE"]
  network_mode              = "awsvpc"
  cpu                        = "512"
  memory                     = "1024"

  container_definitions = jsonencode([
    {
      name  = each.value
      image = "${var.aws_account_id}.dkr.ecr.${var.aws_region}.amazonaws.com/aquamind-${each.value}:latest"
      portMappings = [
        { containerPort = 8000, protocol = "tcp" }
      ]
      environment = [
        { name = "DATABASE_URL", value = "cockroachdb://<user>:<password>@<host>:26257/aquamind" }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = "/aquamind/${each.value}"
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }
    }
  ])
}

resource "aws_ecs_service" "service" {
  for_each        = toset(var.services)
  name            = each.value
  cluster         = aws_ecs_cluster.aquamind.id
  task_definition = aws_ecs_task_definition.service[each.value].arn
  desired_count   = 2
  launch_type     = "FARGATE"

  # Horizontal auto-scaling target tracking on request count / CPU would
  # attach here via aws_appautoscaling_target / aws_appautoscaling_policy
  # (FR-2.8: "horizontal auto-scaling of stateless services based on
  # ingestion and simulation load").
}
