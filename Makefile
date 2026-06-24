.PHONY: network vllm-up vllm-down litellm-up litellm-down \
       train-up train-down \
       observe-up observe-down observe-batch \
       preset-list preset-apply config-render \
       benchmark-vllm benchmark-gateway eval-quality \
       validate validate-compose validate-health validate-registry \
       validate-quick test-integration test-platform release-check \
       guardrails down help

N ?= 10
PROMPT ?= Explain briefly what a neural network is.
COMPOSE ?= $(shell if docker compose version >/dev/null 2>&1; then printf 'docker compose'; elif command -v docker-compose >/dev/null 2>&1; then printf 'docker-compose'; else printf 'docker compose'; fi)

# --- Serving ---

network: ## Create llm-net Docker network
	docker network create llm-net 2>/dev/null || true

vllm-up: ## Start vLLM runtime
	./llm-local serve vllm up

vllm-down:
	./llm-local serve vllm down

litellm-up: ## Start LiteLLM gateway
	./llm-local serve litellm up

litellm-down:
	./llm-local serve litellm down

# --- Training ---

train-up: ## Start training environment
	./llm-local train up

train-down:
	./llm-local train down

# --- Observation ---

observe-up: ## Start real-time monitoring (Prometheus + Grafana)
	./llm-local observe up

observe-down:
	./llm-local observe down

observe-batch: ## Generate batch report from benchmark results
	./llm-local observe batch

# --- Model Management ---

preset-list: ## List serving presets
	./llm-local preset list

preset-apply: PRESET ?= vllm-sample-chat
preset-apply: ## Set active serving preset (PRESET=id)
	./llm-local preset apply $(PRESET)

config-render: ## Render active preset into runtime .env files
	./llm-local config render

# --- Evaluation ---

benchmark-vllm: MODEL ?= local/sample-chat-small
benchmark-vllm: ## Benchmark vLLM directly (MODEL=x N=x)
	./llm-local eval run --target vllm --model $(MODEL) --num-requests $(N) --prompt "$(PROMPT)"

benchmark-gateway: MODEL ?= local-vllm
benchmark-gateway: ## Benchmark LiteLLM gateway (MODEL=x N=x)
	./llm-local eval run --target litellm --model $(MODEL) --num-requests $(N) --prompt "$(PROMPT)" --api-key $${LITELLM_MASTER_KEY:-sk-local-litellm}

eval-quality: ## Run lm-eval quality benchmark
	./llm-local eval quality

# --- Validation ---

validate-compose: ## Verify docker-compose configs are valid
	$(COMPOSE) -f serving/vllm/docker-compose.yml config >/dev/null
	$(COMPOSE) -f serving/litellm/docker-compose.yml config >/dev/null
	$(COMPOSE) -f training/unsloth/docker-compose.yml config >/dev/null
	$(COMPOSE) -f training/mlflow/docker-compose.yml config >/dev/null
	$(COMPOSE) -f evaluation/docker-compose.yml config >/dev/null
	$(COMPOSE) -f observation/docker-compose.yml config >/dev/null
	$(COMPOSE) -f tests/integration/release_registry/docker-compose.yml config >/dev/null
	@echo "All compose configs valid."

validate-health: ## Check running container healthchecks
	@echo "Checking vLLM..." && docker inspect --format='{{.State.Health.Status}}' vllm 2>/dev/null || echo "not running"
	@echo "Checking LiteLLM..." && docker inspect --format='{{.State.Health.Status}}' litellm 2>/dev/null || echo "not running"

validate-registry: ## Check model registry paths
	./llm-local model validate

validate-quick: ## Run quick static validation ladder
	./llm-local validate quick

test-integration: ## Run integration validation ladder
	./llm-local validate integration

test-platform: ## Run live platform validation ladder
	./llm-local validate platform $(if $(SERVICE),--service $(SERVICE),)

release-check: ## Run release validation ladder on a prepared runtime host
	./llm-local validate release $(if $(SERVICE),--service $(SERVICE),)

validate: validate-quick ## Run default validation

guardrails: ## Check GPU policy, ports, service health, and model/runtime compatibility
	./llm-local guardrails --all

# --- Lifecycle ---

down: ## Stop all services
	-./llm-local serve vllm down
	-./llm-local serve litellm down
	-./llm-local train down
	-./llm-local observe down

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
