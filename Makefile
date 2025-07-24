# WebSocket Test Service Makefile

# Variables
IMAGE_NAME = websocket-test
IMAGE_TAG = latest
CONTAINER_NAME = websocket-test
K8S_NAMESPACE = default

# Help target
.PHONY: help
help:
	@echo "WebSocket Test Service Makefile"
	@echo "================================"
	@echo ""
	@echo "Docker Commands:"
	@echo "  build          - Build Docker image"
	@echo "  run            - Run single container"
	@echo "  run-multi      - Run multiple containers for LB testing"
	@echo "  stop           - Stop all containers"
	@echo "  clean          - Remove containers and images"
	@echo ""
	@echo "Kubernetes Commands:"
	@echo "  k8s-deploy     - Deploy to Kubernetes"
	@echo "  k8s-delete     - Delete from Kubernetes"
	@echo "  k8s-status     - Check deployment status"
	@echo "  k8s-logs       - Show pod logs"
	@echo "  k8s-port-forward - Setup port forwarding"
	@echo ""
	@echo "Testing Commands:"
	@echo "  test-deps      - Install test dependencies"
	@echo "  test-docker    - Test Docker deployment"
	@echo "  test-k8s       - Test Kubernetes deployment"
	@echo "  test-lb        - Run load balancer test"

# Docker Commands
.PHONY: build
build:
	@echo "🔨 Building Docker image..."
	docker build -t $(IMAGE_NAME):$(IMAGE_TAG) .

.PHONY: run
run: build
	@echo "🚀 Running single container..."
	docker run -d --name $(CONTAINER_NAME) \
		-p 8080:8080 -p 8765:8765 \
		$(IMAGE_NAME):$(IMAGE_TAG)
	@echo "✅ Container started: http://localhost:8080"

.PHONY: run-multi
run-multi: build
	@echo "🚀 Running multiple containers for load balancing test..."
	@docker run -d --name ws-test-1 -p 8081:8080 -p 8766:8765 $(IMAGE_NAME):$(IMAGE_TAG)
	@docker run -d --name ws-test-2 -p 8082:8080 -p 8767:8765 $(IMAGE_NAME):$(IMAGE_TAG)
	@docker run -d --name ws-test-3 -p 8083:8080 -p 8768:8765 $(IMAGE_NAME):$(IMAGE_TAG)
	@echo "✅ Multiple containers started:"
	@echo "   - http://localhost:8081 (ws-test-1)"
	@echo "   - http://localhost:8082 (ws-test-2)"
	@echo "   - http://localhost:8083 (ws-test-3)"

.PHONY: stop
stop:
	@echo "🛑 Stopping containers..."
	@docker stop $(CONTAINER_NAME) ws-test-1 ws-test-2 ws-test-3 2>/dev/null || true
	@docker rm $(CONTAINER_NAME) ws-test-1 ws-test-2 ws-test-3 2>/dev/null || true
	@echo "✅ Containers stopped and removed"

.PHONY: clean
clean: stop
	@echo "🧹 Cleaning up images..."
	@docker rmi $(IMAGE_NAME):$(IMAGE_TAG) 2>/dev/null || true
	@echo "✅ Images removed"

# Kubernetes Commands
.PHONY: k8s-deploy
k8s-deploy:
	@echo "🚀 Deploying to Kubernetes..."
	kubectl apply -f k8s-deployment.yaml
	@echo "✅ Deployment applied"

.PHONY: k8s-delete
k8s-delete:
	@echo "🗑️  Deleting from Kubernetes..."
	kubectl delete -f k8s-deployment.yaml
	@echo "✅ Resources deleted"

.PHONY: k8s-status
k8s-status:
	@echo "📊 Checking deployment status..."
	@echo ""
	@echo "Pods:"
	kubectl get pods -l app=websocket-test
	@echo ""
	@echo "Services:"
	kubectl get svc -l app=websocket-test
	@echo ""
	@echo "Deployment:"
	kubectl get deployment websocket-test-service

.PHONY: k8s-logs
k8s-logs:
	@echo "📄 Showing pod logs..."
	kubectl logs -l app=websocket-test --tail=50

.PHONY: k8s-port-forward
k8s-port-forward:
	@echo "🔗 Setting up port forwarding..."
	@echo "   HTTP: http://localhost:8080"
	@echo "   WebSocket: ws://localhost:8765"
	@echo "   Press Ctrl+C to stop"
	kubectl port-forward svc/websocket-test-service 8080:8080 8765:8765

# Testing Commands
.PHONY: test-deps
test-deps:
	@echo "📦 Installing test dependencies..."
	pip install websockets aiohttp

.PHONY: test-docker
test-docker: run
	@echo "🧪 Testing Docker deployment..."
	@sleep 5  # Wait for container to start
	python test_lb.py --host localhost --connections 5
	@$(MAKE) stop

.PHONY: test-k8s
test-k8s:
	@echo "🧪 Testing Kubernetes deployment..."
	@echo "Make sure to run 'make k8s-port-forward' in another terminal first"
	python test_lb.py --host localhost --connections 5

.PHONY: test-lb
test-lb:
	@echo "🧪 Running load balancer test..."
	python test_lb.py --host localhost --connections 10

# Development Commands
.PHONY: dev-run
dev-run:
	@echo "🔧 Running in development mode..."
	python app.py

.PHONY: dev-install
dev-install:
	@echo "📦 Installing all dependencies..."
	pip install -r requirements.txt
	@$(MAKE) test-deps

# Utility Commands
.PHONY: health-check
health-check:
	@echo "🏥 Checking service health..."
	curl -s http://localhost:8080/health | jq .

.PHONY: show-containers
show-containers:
	@echo "📋 Current containers:"
	docker ps | grep websocket-test || echo "No websocket-test containers running"

# Default target
.DEFAULT_GOAL := help 