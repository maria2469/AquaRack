# AWS networking blueprint (SDD Phase 2, Section 4 — Figure 3 topology).
# Illustrative only — see ../README.md before applying.

variable "aws_region" {
  default = "us-east-1"
}

variable "vpc_cidr" {
  default = "10.20.0.0/16"
}

provider "aws" {
  region = var.aws_region
}

data "aws_availability_zones" "available" {
  state = "available"
}

resource "aws_vpc" "aquamind" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags = {
    Name = "aquamind-ai-phase2"
  }
}

resource "aws_internet_gateway" "aquamind" {
  vpc_id = aws_vpc.aquamind.id
  tags = {
    Name = "aquamind-ai-igw"
  }
}

resource "aws_subnet" "public" {
  count                   = 2
  vpc_id                  = aws_vpc.aquamind.id
  cidr_block              = cidrsubnet(var.vpc_cidr, 8, count.index + 10)
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true
  tags = {
    Name = "aquamind-public-${count.index}"
  }
}

resource "aws_subnet" "private" {
  count             = 2
  vpc_id            = aws_vpc.aquamind.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, count.index)
  availability_zone = data.aws_availability_zones.available.names[count.index]
  tags = {
    Name = "aquamind-private-${count.index}"
  }
}

# ALB (Section 4.1: "Application Load Balancer — Routes traffic to
# ECS/EKS services in the private subnet") would attach to the public
# subnets; the ECS services themselves run in the private subnets.
