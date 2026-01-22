.PHONY: docker-build docker-run test clean help

IMAGE_NAME ?= llm-inference-gateway
TAG ?= latest
PORT ?= 8000

help:
	@echo "Available targets:"
	@echo "  docker-build    Build Docker images"
	@echo "  docker-run      Run the gateway container"
	@echo "  test           Run tests"
	@echo "  clean          Stop and remove containers"
	@echo ""
	@echo "Variables:"
	@echo "  IMAGE_NAME=$(IMAGE_NAME)"
	@echo "  TAG=$(TAG)"
	@echo "  PORT=$(PORT)"

docker-build:
	@echo "Building gateway image..."
	docker build -f Dockerfile.gateway -t $(IMAGE_NAME):$(TAG) .
	@echo "Building backend image..."
	docker build -f Dockerfile.backend -t $(IMAGE_NAME)-backend:$(TAG) .
	@echo "Build complete!"

docker-run:
	@echo "Running gateway container on port $(PORT)..."
	docker run -d \
		--name llm-gateway \
		-p $(PORT):8000 \
		$(IMAGE_NAME):$(TAG)
	@echo "Gateway running at http://localhost:$(PORT)"
	@echo "Check health: curl http://localhost:$(PORT)/healthz"

test:
	@echo "Running tests..."
	pytest tests/ -v
	@echo "Tests complete!"

clean:
	@echo "Stopping and removing containers..."
	-docker stop llm-gateway 2>/dev/null || true
	-docker rm llm-gateway 2>/dev/null || true
	@echo "Cleanup complete!"

docker-test: docker-build
	@echo "Running tests in Docker..."
	docker run --rm $(IMAGE_NAME):$(TAG) pytest tests/ -v
