provider "aws" {
  access_key = "${var.aws_access_key}"
  secret_key = "${var.aws_secret_key}"
  region = "${var.region}"
}

# Generic ALB - alb.tf

# Generic ECS cluster infra - in ecs-cluster.tf

# Pushpin container and deployment - in pushpin.tf

# Backend process container and deployment - in backend.tf

# Dynamo caching table and stream - in dynamo.tf
