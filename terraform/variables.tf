variable "fly_api_token" {
  description = "Fly.io API token (export FLY_API_TOKEN or set in terraform.tfvars)"
  type        = string
  sensitive   = true
}

variable "fly_org" {
  description = "Fly.io organization slug"
  type        = string
  default     = "personal"
}

variable "fly_region" {
  description = "Fly.io primary region"
  type        = string
  default     = "ewr"
}

variable "app_name" {
  description = "Fly app name (must be globally unique on Fly)"
  type        = string
  default     = "ospsd-outlook-calendar-team12"
}

variable "image" {
  description = "Container image to deploy (e.g. registry.fly.io/<app>:latest)"
  type        = string
  default     = "registry.fly.io/ospsd-outlook-calendar-team12:latest"
}
