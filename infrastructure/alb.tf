resource "aws_alb" "main" {
  name            = "restream"
  subnets         = ["${split(",", var.ecs_cluster_subnet_ids)}"]
  security_groups = ["${aws_security_group.alb.id}"] 
}

resource "aws_alb_listener" "pushpin" {
  load_balancer_arn = "${aws_alb.main.id}"
  port              = "${var.pushpin_external_port}"
  protocol          = "HTTP"

  default_action {
    target_group_arn = "${aws_alb_target_group.pushpin.id}"
    type             = "forward"
  }
}

resource "aws_alb_listener" "pushpin_control" {
  load_balancer_arn = "${aws_alb.main.id}"
  port              = "${var.pushpin_control_port}"
  protocol          = "HTTP"

  default_action {
    target_group_arn = "${aws_alb_target_group.pushpin.id}"
    type             = "forward"
  }
}

resource "aws_alb_listener" "backend" {
  load_balancer_arn = "${aws_alb.main.id}"
  port              = "${var.backend_port}"
  protocol          = "HTTP"

  default_action {
    target_group_arn = "${aws_alb_target_group.backend.id}"
    type             = "forward"
  }
}

resource "aws_alb_target_group" "pushpin" {
  name     = "pushpin"
  port     = "${var.pushpin_external_port}"
  protocol = "HTTP"
  vpc_id   = "${var.vpc_id}"
}

resource "aws_alb_target_group" "pushpin_control" {
  name     = "pushpin-control"
  port     = "${var.pushpin_control_port}"
  protocol = "HTTP"
  vpc_id   = "${var.vpc_id}"
}

#############
# FIXME need to add the pushpin instance manually to the pushpin_control target group at the moment
#############

# # The pushpin container has two ports that need to be exposed, so we need to
# # explicitly attach the second one (the first is attached as part of aws_ecs_service.pushpin)
# resource "aws_alb_target_group_attachment" "pushpin_control" {
#   port             = "${var.pushpin_external_port}"
#   target_id        = "${aws_ecs_service.pushpin.id}"
#   target_group_arn = "${aws_alb_target_group.pushpin_control.arn}"
# }

resource "aws_alb_target_group" "backend" {
  name     = "backend"
  port     = "${var.backend_port}"
  protocol = "HTTP"
  vpc_id   = "${var.vpc_id}"
}

resource "aws_security_group" "alb" {
  name = "alb"
  description = "Security group for the ALB"
  vpc_id = "${var.vpc_id}"

  # Outbound Everything
  egress {
    from_port = 0
    to_port = 0
    protocol = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port = "${var.pushpin_external_port}"
    to_port = "${var.pushpin_external_port}"
    protocol = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port = "${var.pushpin_control_port}"
    to_port = "${var.pushpin_control_port}"
    protocol = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port = "${var.backend_port}"
    to_port = "${var.backend_port}"
    protocol = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  lifecycle {
    create_before_destroy = true
  }
}
