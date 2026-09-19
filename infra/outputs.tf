output "application_url" {
  description = "Load balancer URL."
  value       = "${var.certificate_arn == null ? "http" : "https"}://${aws_lb.app.dns_name}"
}

output "ecr_repository_url" {
  description = "Repository URL used by the deployment workflow."
  value       = aws_ecr_repository.app.repository_url
}

output "ecr_repository_name" {
  description = "Repository name used to validate rollback tags."
  value       = aws_ecr_repository.app.name
}

output "ecs_cluster_name" {
  value = aws_ecs_cluster.app.name
}

output "ecs_service_name" {
  value = aws_ecs_service.app.name
}

output "database_endpoint" {
  description = "Private RDS endpoint."
  value       = aws_db_instance.postgres.endpoint
}

output "database_master_secret_arn" {
  description = "RDS-managed Secrets Manager secret consumed directly by ECS."
  value       = aws_db_instance.postgres.master_user_secret[0].secret_arn
}
