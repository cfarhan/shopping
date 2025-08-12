terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.1"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# Strong random password if not provided
resource "random_password" "db_password" {
  length           = 32
  special          = true
  override_characters = "!@#%^*()-_=+[]{};:,.?/" # avoid quotes and backslashes for URL
}

# Use default VPC's default security group or create a simple SG
resource "aws_security_group" "rds_public" {
  name_prefix = "${var.project_name}-rds-public-"
  description = "Public access for Postgres (use only if you cannot IP-whitelist)"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "PostgreSQL"
    from_port   = 5432
    to_port     = 5432
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
    ignore_changes = [ingress]
  }

  tags = {
    Name        = "${var.project_name}-rds-public"
    Environment = var.environment
  }
}

data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

# Optional: Parameter group to enforce SSL (Heroku requires SSL by default)
resource "aws_db_parameter_group" "postgres" {
  name        = "${var.project_name}-pg-params"
  family      = "postgres15"
  description = "Parameter group for ${var.project_name}"

  parameter {
    name  = "rds.force_ssl"
    value = "1"
  }
}

resource "aws_db_subnet_group" "default_vpc" {
  name       = "${var.project_name}-default-vpc-subnets"
  subnet_ids = data.aws_subnets.default.ids
}

resource "aws_db_instance" "this" {
  identifier = "${var.project_name}-pg"

  engine                 = "postgres"
  engine_version         = "15.7"
  instance_class         = var.db_instance_class
  allocated_storage      = var.db_allocated_storage
  max_allocated_storage  = 100
  storage_type           = "gp2"
  storage_encrypted      = true

  db_name                = var.db_name
  username               = var.db_username
  password               = var.db_password != "" ? var.db_password : random_password.db_password.result

  publicly_accessible    = true
  vpc_security_group_ids = [aws_security_group.rds_public.id]
  db_subnet_group_name   = aws_db_subnet_group.default_vpc.name
  parameter_group_name   = aws_db_parameter_group.postgres.name

  backup_retention_period = 7
  skip_final_snapshot     = true
  deletion_protection     = false
  auto_minor_version_upgrade = true
  monitoring_interval     = 0

  tags = {
    Name        = "${var.project_name}-rds"
    Environment = var.environment
  }
} 