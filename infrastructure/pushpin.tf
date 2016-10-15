# The ECS Task that specifies what Docker containers we need to run pushpin
resource "aws_ecs_task_definition" "pushpin" {
  family = "pushpin"
  container_definitions = <<EOF
[
  {
    "name": "pushpin",
    "image": "${var.pushpin_image}:${var.pushpin_version}",
    "cpu": 1024,
    "memory": 768,
    "essential": true,
    "portMappings": [
      {
        "containerPort": ${var.pushpin_external_port},
        "hostPort": ${var.pushpin_external_port},
        "protocol": "tcp"
      },
      {
        "containerPort": ${var.pushpin_control_port},
        "hostPort": ${var.pushpin_control_port},
        "protocol": "tcp"
      }
    ],
    "environment": [
      {
        "name": "target",
        "value": "${aws_alb.main.dns_name}:${var.backend_port}"
      }
    ]
  }
]
EOF
}

# A long-running ECS Service for pushpin
resource "aws_ecs_service" "pushpin" {
  name = "pushpin"
  cluster = "${aws_ecs_cluster.restream_cluster.id}"
  task_definition = "${aws_ecs_task_definition.pushpin.arn}"
  depends_on = ["aws_iam_role_policy.ecs_service_policy"]
  desired_count = 1
  deployment_minimum_healthy_percent = 100
  iam_role = "${aws_iam_role.ecs_service_role.arn}"
  load_balancer {
    target_group_arn = "${aws_alb_target_group.pushpin.id}"
    container_name = "pushpin"
    container_port = "${var.pushpin_external_port}"
  }

  depends_on = [
    "aws_iam_role_policy.ecs_service_policy",
    "aws_alb_listener.pushpin",
  ]
}
