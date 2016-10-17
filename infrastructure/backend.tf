# The ECS Task that specifies what Docker containers we need to run pushpin
resource "aws_ecs_task_definition" "backend" {
  family = "backend"
  container_definitions = <<EOF
[
  {
    "name": "backend",
    "image": "${var.backend_image}:${var.backend_version}",
    "cpu": 1024,
    "memory": 768,
    "essential": true,
    "portMappings": [
      {
        "containerPort": ${var.backend_port},
        "hostPort": ${var.backend_port},
        "protocol": "tcp"
      }
    ],
    "environment": [
      { "name": "AWS_ACCESS_KEY_ID", "value": "${var.aws_access_key}" },
      { "name": "AWS_SECRET_ACCESS_KEY", "value": "${var.aws_secret_key}" },
      { "name": "AWS_DEFAULT_REGION", "value": "${var.region}" },
      { "name": "PUSHPIN_HOSTNAME", "value": "${aws_alb.main.dns_name}" },
      { "name": "PUSHPIN_PORT", "value": "${var.backend_port}" },
      { "name": "KEYS_BUCKET", "value": "${var.keys_bucket}" },
      { "name": "KEYS_OBJECT", "value": "${var.keys_object}" },
      { "name": "MESSAGE_CACHE_TABLE", "value": "${var.message_cache_table}" }
    ]
  }
]
EOF
}

# A long-running ECS Service for the backend
resource "aws_ecs_service" "backend" {
  name = "backend"
  cluster = "${aws_ecs_cluster.restream_cluster.id}"
  task_definition = "${aws_ecs_task_definition.backend.arn}"
  depends_on = ["aws_iam_role_policy.ecs_service_policy"]
  desired_count = 1
  deployment_minimum_healthy_percent = 100
  iam_role = "${aws_iam_role.ecs_service_role.arn}"
  load_balancer {
    target_group_arn = "${aws_alb_target_group.backend.id}"
    container_name = "backend"
    container_port = "${var.backend_port}"
  }

  depends_on = [
    "aws_iam_role_policy.ecs_service_policy",
    "aws_alb_listener.backend",
    "aws_alb_target_group.backend"
  ]
}
