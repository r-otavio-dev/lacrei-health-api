locals {
  name = "${var.project_name}-${var.environment}"

  container_environment = merge({
    DJANGO_SETTINGS_MODULE = "config.settings"
    DJANGO_ENV             = "production"
    DJANGO_DEBUG           = "false"
    DJANGO_ALLOWED_HOSTS   = "127.0.0.1,${aws_lb.app.dns_name}"
    # TLS is terminated and HTTP-to-HTTPS redirect is enforced by the ALB. Keeping
    # this false also allows the ALB and container to call the HTTP health probe.
    DJANGO_SECURE_SSL_REDIRECT = "false"
    POSTGRES_DB                = var.database_name
    POSTGRES_USER              = var.database_username
    POSTGRES_HOST              = aws_db_instance.postgres.address
    POSTGRES_PORT              = tostring(aws_db_instance.postgres.port)
    POSTGRES_SSLMODE           = "require"
    DB_HOST                    = aws_db_instance.postgres.address
    DB_PORT                    = tostring(aws_db_instance.postgres.port)
    DB_CONNECT_TIMEOUT         = "60"
    RUN_MIGRATIONS             = "1"
    COLLECT_STATIC             = "1"
    PORT                       = tostring(var.container_port)
  }, var.additional_environment)
}

data "aws_availability_zones" "available" {
  state = "available"
}

resource "aws_vpc" "app" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = { Name = local.name }
}

resource "aws_internet_gateway" "app" {
  vpc_id = aws_vpc.app.id
  tags   = { Name = local.name }
}

resource "aws_subnet" "public" {
  count = 2

  vpc_id                  = aws_vpc.app.id
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  cidr_block              = cidrsubnet(var.vpc_cidr, 8, count.index)
  map_public_ip_on_launch = true

  tags = { Name = "${local.name}-public-${count.index + 1}" }
}

resource "aws_subnet" "database" {
  count = 2

  vpc_id            = aws_vpc.app.id
  availability_zone = data.aws_availability_zones.available.names[count.index]
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, count.index + 10)

  tags = { Name = "${local.name}-database-${count.index + 1}" }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.app.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.app.id
  }

  tags = { Name = "${local.name}-public" }
}

resource "aws_route_table_association" "public" {
  count = 2

  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_security_group" "alb" {
  name_prefix = "${local.name}-alb-"
  description = "Public HTTP and HTTPS ingress to the load balancer"
  vpc_id      = aws_vpc.app.id

  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_security_group" "ecs" {
  name_prefix = "${local.name}-ecs-"
  description = "Only the load balancer can reach application tasks"
  vpc_id      = aws_vpc.app.id

  ingress {
    from_port       = var.container_port
    to_port         = var.container_port
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_security_group" "database" {
  name_prefix = "${local.name}-database-"
  description = "PostgreSQL ingress from ECS tasks only"
  vpc_id      = aws_vpc.app.id

  ingress {
    description     = "PostgreSQL from application tasks"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_db_subnet_group" "app" {
  name       = local.name
  subnet_ids = aws_subnet.database[*].id
  tags       = { Name = local.name }
}

resource "aws_db_instance" "postgres" {
  identifier = local.name

  engine         = "postgres"
  engine_version = var.database_engine_version
  instance_class = var.database_instance_class

  db_name  = var.database_name
  username = var.database_username
  port     = 5432

  manage_master_user_password = true

  allocated_storage     = var.database_allocated_storage
  max_allocated_storage = var.database_max_allocated_storage
  storage_type          = "gp3"
  storage_encrypted     = true

  db_subnet_group_name   = aws_db_subnet_group.app.name
  vpc_security_group_ids = [aws_security_group.database.id]
  publicly_accessible    = false
  multi_az               = var.database_multi_az

  backup_retention_period = var.database_backup_retention_days
  backup_window           = "03:00-04:00"
  maintenance_window      = "sun:04:00-sun:05:00"
  copy_tags_to_snapshot   = true

  deletion_protection       = var.database_deletion_protection
  skip_final_snapshot       = var.database_skip_final_snapshot
  final_snapshot_identifier = var.database_skip_final_snapshot ? null : "${local.name}-final"

  auto_minor_version_upgrade = true
  apply_immediately          = false
}

resource "aws_ecr_repository" "app" {
  name                 = local.name
  image_tag_mutability = "IMMUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }
}

resource "aws_ecr_lifecycle_policy" "app" {
  repository = aws_ecr_repository.app.name
  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep the 30 newest deployable images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 30
      }
      action = { type = "expire" }
    }]
  })
}

resource "aws_cloudwatch_log_group" "app" {
  name              = "/ecs/${local.name}"
  retention_in_days = var.log_retention_days
}

resource "aws_ecs_cluster" "app" {
  name = local.name

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

data "aws_iam_policy_document" "ecs_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    effect  = "Allow"

    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "execution" {
  name               = "${local.name}-execution"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume_role.json
}

resource "aws_iam_role_policy_attachment" "execution" {
  role       = aws_iam_role.execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

data "aws_iam_policy_document" "secrets" {
  statement {
    actions   = ["secretsmanager:GetSecretValue"]
    resources = concat(values(var.secret_arns), [aws_db_instance.postgres.master_user_secret[0].secret_arn])
  }
}

resource "aws_iam_role_policy" "secrets" {
  name   = "read-runtime-secrets"
  role   = aws_iam_role.execution.id
  policy = data.aws_iam_policy_document.secrets.json
}

resource "aws_iam_role" "task" {
  name               = "${local.name}-task"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume_role.json
}

resource "aws_lb" "app" {
  name               = substr(local.name, 0, 32)
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = aws_subnet.public[*].id
}

resource "aws_lb_target_group" "app" {
  name        = substr(local.name, 0, 32)
  port        = var.container_port
  protocol    = "HTTP"
  target_type = "ip"
  vpc_id      = aws_vpc.app.id

  deregistration_delay = 30

  health_check {
    enabled             = true
    path                = var.health_check_path
    matcher             = "200"
    interval            = 30
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.app.arn
  port              = 80
  protocol          = "HTTP"

  dynamic "default_action" {
    for_each = var.certificate_arn == null ? [1] : []
    content {
      type             = "forward"
      target_group_arn = aws_lb_target_group.app.arn
    }
  }

  dynamic "default_action" {
    for_each = var.certificate_arn == null ? [] : [1]
    content {
      type = "redirect"
      redirect {
        port        = "443"
        protocol    = "HTTPS"
        status_code = "HTTP_301"
      }
    }
  }

  lifecycle {
    precondition {
      condition = (
        var.environment != "production" ||
        try(length(trimspace(var.certificate_arn)) > 0, false)
      )
      error_message = "Production requires certificate_arn so the ALB can enforce HTTPS."
    }
  }
}

resource "aws_lb_listener" "https" {
  count = var.certificate_arn == null ? 0 : 1

  load_balancer_arn = aws_lb.app.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = var.certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app.arn
  }
}

resource "aws_ecs_task_definition" "app" {
  family                   = local.name
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.task_cpu
  memory                   = var.task_memory
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }

  container_definitions = jsonencode([{
    name                   = "app"
    image                  = "${aws_ecr_repository.app.repository_url}:${var.image_tag}"
    essential              = true
    readonlyRootFilesystem = false

    portMappings = [{
      containerPort = var.container_port
      hostPort      = var.container_port
      protocol      = "tcp"
    }]

    environment = [for key, value in local.container_environment : {
      name  = key
      value = value
    }]

    secrets = concat(
      [for key, value in var.secret_arns : {
        name      = key
        valueFrom = value
      }],
      [{
        name      = "POSTGRES_PASSWORD"
        valueFrom = "${aws_db_instance.postgres.master_user_secret[0].secret_arn}:password::"
      }]
    )

    healthCheck = {
      command = [
        "CMD-SHELL",
        "python -c \"import urllib.request; urllib.request.urlopen('http://127.0.0.1:${var.container_port}${var.health_check_path}', timeout=3)\" || exit 1"
      ]
      interval    = 30
      timeout     = 5
      retries     = 3
      startPeriod = 60
    }

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.app.name
        awslogs-region        = var.aws_region
        awslogs-stream-prefix = "app"
      }
    }
  }])

  lifecycle {
    precondition {
      condition = (
        var.environment != "production" ||
        try(length(trimspace(var.additional_environment["DJANGO_ALLOWED_HOSTS"])) > 0, false)
      )
      error_message = "Production requires DJANGO_ALLOWED_HOSTS in additional_environment."
    }
  }
}

resource "aws_ecs_service" "app" {
  name            = local.name
  cluster         = aws_ecs_cluster.app.id
  task_definition = aws_ecs_task_definition.app.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  deployment_minimum_healthy_percent = 100
  deployment_maximum_percent         = 200
  health_check_grace_period_seconds  = 60
  enable_execute_command             = true

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  network_configuration {
    assign_public_ip = true
    subnets          = aws_subnet.public[*].id
    security_groups  = [aws_security_group.ecs.id]
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.app.arn
    container_name   = "app"
    container_port   = var.container_port
  }

  depends_on = [aws_lb_listener.http]
}
