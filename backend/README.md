# Restream Backend 
This folder contains the restream backend process, as well as a Dockerfile to package it into an image. 

This docker image is referenced in the terraform files. If you modify it and publish it under a new tag, you must change the value of the `backend_image` terraform variable that is defined in `infrastructure/vars.tf`.

To build and publish a new version of the the image (from this directory):

```bash
docker login
docker build -t <username>/<imagename>:latest .
docker push <username>/<imagename>
```

In order to force an update to the existing backend ECS instances that house the container:

```bash
cd ..
apex infra taint "aws_ecs_task_definition.backend"
apex infra plan
apex infra apply
```

FIXME need to figure out best way of getting ECS service to use the new task; see https://forums.aws.amazon.com/thread.jspa?threadID=179271

To run this container locally, use 

```bash
docker run -p 5000:5000 \
  -e AWS_ACCESS_KEY_ID='<access-key>' \
  -e AWS_SECRET_ACCESS_KEY='<secret-key>' \
  -e AWS_DEFAULT_REGION='<region>' \
  beaucronin/restream-backend:latest
```