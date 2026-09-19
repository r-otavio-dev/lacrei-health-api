variable "aws_region" {
  description = "AWS region for all resources."
  type        = string
}

variable "project_name" {
  description = "Short name used in resource names."
  type        = string
  default     = "lacrei-api"
}

variable "environment" {
  description = "Deployment environment name."
  type        = string

  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "environment must be staging or production."
  }
}

variable "image_tag" {
  description = "Immutable container image tag, normally the Git commit SHA."
  type        = string

  validation {
    condition     = length(trimspace(var.image_tag)) >= 7
    error_message = "image_tag must be an immutable tag of at least seven characters."
  }
}

variable "vpc_cidr" {
  description = "CIDR assigned to the environment VPC."
  type        = string
  default     = "10.20.0.0/16"
}

variable "container_port" {
  description = "Port exposed by Gunicorn."
  type        = number
  default     = 8000
}

variable "desired_count" {
  description = "Number of Fargate tasks."
  type        = number
  default     = 2
}

variable "task_cpu" {
  description = "Fargate task CPU units."
  type        = number
  default     = 512
}

variable "task_memory" {
  description = "Fargate task memory in MiB."
  type        = number
  default     = 1024
}

variable "health_check_path" {
  description = "Unauthenticated HTTP readiness endpoint."
  type        = string
  default     = "/health/ready/"
}

variable "database_name" {
  description = "Initial PostgreSQL database name."
  type        = string
  default     = "lacrei"
}

variable "database_username" {
  description = "PostgreSQL master username. The password is generated and managed by RDS in Secrets Manager."
  type        = string
  default     = "lacrei_admin"
}

variable "database_engine_version" {
  description = "RDS PostgreSQL engine version."
  type        = string
  default     = "17.6"
}

variable "database_instance_class" {
  description = "RDS instance class."
  type        = string
  default     = "db.t4g.micro"
}

variable "database_allocated_storage" {
  description = "Initial RDS gp3 storage in GiB."
  type        = number
  default     = 20
}

variable "database_max_allocated_storage" {
  description = "Maximum storage autoscaling limit in GiB."
  type        = number
  default     = 100
}

variable "database_multi_az" {
  description = "Whether RDS uses a synchronous standby in another AZ."
  type        = bool
  default     = false
}

variable "database_backup_retention_days" {
  description = "Automated RDS backup retention in days."
  type        = number
  default     = 7
}

variable "database_deletion_protection" {
  description = "Protect the database from accidental deletion."
  type        = bool
  default     = true
}

variable "database_skip_final_snapshot" {
  description = "Skip the final database snapshot on destroy. Keep false for production."
  type        = bool
  default     = false
}

variable "certificate_arn" {
  description = "Optional ACM certificate ARN. When set, HTTP redirects to HTTPS."
  type        = string
  default     = null
  nullable    = true

  validation {
    condition     = var.certificate_arn == null || length(trimspace(var.certificate_arn)) > 0
    error_message = "certificate_arn must be null or a non-empty ACM certificate ARN."
  }
}

variable "secret_arns" {
  description = "Map of extra container variables (for example DJANGO_SECRET_KEY) to Secrets Manager ARNs. Values are never stored in Terraform."
  type        = map(string)
  default     = {}
  sensitive   = true

  validation {
    condition     = contains(keys(var.secret_arns), "DJANGO_SECRET_KEY")
    error_message = "secret_arns must include DJANGO_SECRET_KEY pointing to a Secrets Manager secret ARN."
  }
}

variable "additional_environment" {
  description = "Non-sensitive container environment variables."
  type        = map(string)
  default     = {}
}

variable "log_retention_days" {
  description = "CloudWatch log retention."
  type        = number
  default     = 30
}

variable "tags" {
  description = "Additional AWS resource tags."
  type        = map(string)
  default     = {}
}
