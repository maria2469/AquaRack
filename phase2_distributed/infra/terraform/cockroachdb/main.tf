# CockroachDB multi-region blueprint (SDD Section 5/19: FR-2.4 —
# "configurable table survival goals (REGIONAL/GLOBAL)"). Illustrative
# only — see ../README.md before applying.
#
# CockroachDB Cloud clusters are typically provisioned via the CockroachDB
# Terraform provider (registry.terraform.io/cockroachdb/cockroach) rather
# than a native AWS resource. This file documents the variables Phase 2's
# schema migration (shared/db/, Section 10.1) expects to be set once that
# provider is configured.

variable "cluster_name" {
  default = "aquamind-ai-phase2"
}

variable "regions" {
  description = "Multi-region CockroachDB cluster regions (Section 5.2)"
  default     = ["us-east-1", "eu-west-1", "ap-southeast-1"]
}

variable "table_locality_overrides" {
  description = <<-EOT
    Per-table locality overrides (Section 5.2): default REGIONAL for
    latency-sensitive operational tables (telemetry, water_model,
    recommendations); GLOBAL only for tables genuinely requiring
    global consistency (Section 20.1 bottleneck watch-list).
  EOT
  default = {
    telemetry       = "REGIONAL"
    water_model     = "REGIONAL"
    recommendations = "REGIONAL"
    sites           = "GLOBAL"
  }
}

# Example (requires the cockroachdb/cockroach provider configured with an
# API key):
#
# resource "cockroach_cluster" "aquamind" {
#   name           = var.cluster_name
#   cloud_provider = "AWS"
#   plan           = "DEDICATED"
#   dedicated_config = {
#     region_nodes = { for r in var.regions : r => 3 }
#   }
# }
