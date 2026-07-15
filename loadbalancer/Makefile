IMAGE_SERVER := loadbalancer-server:latest

.PHONY: build up down restart logs test analyze clean

## Build the backend server image and the load balancer image.
build:
	docker build -t $(IMAGE_SERVER) ./server
	docker compose build

## Build (if needed) and start the load balancer stack in the background.
## The load balancer bootstraps LB_N=3 backend replicas itself on startup.
up: build
	docker compose up -d
	docker compose ps

## Stop and remove the load balancer container plus any backend replicas it spawned.
down:
	docker compose down
	-docker ps -aq --filter "ancestor=$(IMAGE_SERVER)" | xargs -r docker rm -f

restart: down up

## Tail the load balancer's logs.
logs:
	docker compose logs -f loadbalancer

## Run the unit test suite (Task 2/3 logic, no Docker daemon required).
test:
	pip install -r requirements-dev.txt
	pytest -v

## Run the Task 4 performance analysis against a running stack (`make up` first).
analyze:
	python3 analysis/analyze.py

## Remove everything, including built images.
clean: down
	-docker rmi -f $(IMAGE_SERVER) loadbalancer-lb:latest
