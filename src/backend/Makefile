.PHONY: dev lint mypy-lint complex coverage pre-commit sort deploy destroy deps unit infra-tests integration e2e coverage-tests docs lint-docs build format format-fix compare-openapi openapi pr watch update-deps cleanup-changesets wait-for-stack smoke-test ssm-setup
PYTHON := .venv/bin/python3
APP := ../../infra/app.py
.ONESHELL:  # run all commands in a single shell, ensuring it runs within a local virtual env

# Keep Lambda runtime configuration in one place so packaging, dependencies,
# and CDK stay aligned.
PYTHON_RUNTIME_VERSION := 3.14
LAMBDA_RUNTIME_ENUM := PYTHON_3_14
LAMBDA_ARCH_ENUM := X86_64
DOCKER_PLATFORM := linux/amd64
LAYER_BUNDLING_PLATFORM := linux/amd64
LAMBDA_BASE_IMAGE := public.ecr.aws/lambda/python:$(PYTHON_RUNTIME_VERSION)
API_CONSTRUCT_PATH := ../../infra/careervp/api_construct.py

OPENAPI_DIR := ./docs/swagger
CURRENT_OPENAPI := $(OPENAPI_DIR)/openapi.json
LATEST_OPENAPI := openapi_latest.json


dev:
	pip install --upgrade pip pre-commit uv
	pre-commit install
	uv sync
	npm ci

format:
	uv run ruff check . --fix

format-fix:
	uv run ruff format .

lint: format
	@echo "Running mypy"
	$(MAKE) mypy-lint

complex:
	@echo "Running Radon"
	uv run radon cc -e 'tests/*,cdk.out/**,**/cdk.out/**,node_modules/*' .
	@echo "Running xenon"
	uv run xenon --max-absolute C --max-modules A --max-average A -e 'tests/*,.venv/*,cdk.out/**,**/cdk.out/**,node_modules/*' .

pre-commit:
	uv run pre-commit run -a --show-diff-on-failure

mypy-lint:
	uv run mypy --pretty careervp cdk tests

deps:
	uv export --no-dev --no-editable --no-emit-project --no-color --format=requirements-txt > lambda_requirements.txt
	uv export --no-editable --no-emit-project --no-color --format=requirements-txt > dev_requirements.txt

unit:
	uv run pytest tests/unit  --cov-config=.coveragerc --cov=careervp --cov-report xml

build: deps check-runtime
	rm -rf .build/lambdas
	mkdir -p .build/lambdas
	docker run --rm --platform $(DOCKER_PLATFORM) \
		--entrypoint /bin/sh \
		-v $(PWD):/app \
		-w /app \
		$(LAMBDA_BASE_IMAGE) \
		-c "microdnf install -y gcc libxml2-devel libxslt-devel >/dev/null && \
		    pip install --prefer-binary -r lambda_requirements.txt -t .build/lambdas && \
		    chown -R $$(id -u):$$(id -g) .build/lambdas"
	rsync -a careervp .build/lambdas \
		--exclude 'cdk.out' \
		--exclude '.mypy_cache' \
		--exclude '.venv' \
		--exclude '*.log'
	@test -d .build/lambdas/careervp || (echo "ERROR: careervp not found in build" && exit 1)
	@echo "Build verified: careervp package present"
	mkdir -p .build/common_layer
	uv export --no-dev --no-editable --no-emit-project --no-color --format=requirements-txt > .build/common_layer/requirements.txt

check-runtime:
	@python3 scripts/check_runtime.py $(PYTHON_RUNTIME_VERSION) $(LAMBDA_RUNTIME_ENUM) $(LAMBDA_ARCH_ENUM) $(LAYER_BUNDLING_PLATFORM) $(API_CONSTRUCT_PATH)

infra-tests: build
	uv run pytest tests/infrastructure

integration:
	uv run pytest tests/integration  --cov-config=.coveragerc --cov=careervp --cov-report xml

e2e:
	@if ! ls tests/e2e/test_*.py >/dev/null 2>&1; then \
		echo "No e2e tests detected; skipping."; \
	else \
		uv run pytest tests/e2e --cov-config=.coveragerc --cov=careervp --cov-report xml; \
	fi

pr: deps format pre-commit complex lint lint-docs unit deploy coverage-tests e2e openapi

coverage-tests:
	uv run pytest tests/unit tests/integration  --cov-config=.coveragerc --cov=careervp --cov-report xml

deploy: build
	npx cdk acknowledge 34892
	npx cdk deploy --app="$(PYTHON) ${PWD}/../infra/app.py" --require-approval=never

destroy:
	npx cdk acknowledge 34892
	npx cdk destroy --app="$(PYTHON) ${PWD}/../infra/app.py" --force

docs:
	uv run mkdocs serve

lint-docs:
	npx markdownlint-cli2 "docs/**/*.md" --fix

watch:
	npx cdk watch

update-deps:
	@echo "Updating uv dependencies..."
	uv lock --upgrade
	uv sync
	@echo "Updating pre-commit hooks..."
	pre-commit autoupdate
	@echo "Fetching latest CDK version from npm..."
	$(eval LATEST_CDK_VERSION := $(shell npm view aws-cdk version))
	@echo "Found CDK version: $(LATEST_CDK_VERSION)"
	@echo "Updating package.json with latest CDK version..."
	node -e "const fs = require('fs'); const pkg = JSON.parse(fs.readFileSync('package.json')); pkg.dependencies['aws-cdk'] = '$(LATEST_CDK_VERSION)'; fs.writeFileSync('package.json', JSON.stringify(pkg, null, 4));"
	npm i --package-lock-only
	@echo "Installing npm dependencies..."
	npm install
	@echo "All dependencies updated successfully!"

openapi:
	uv run python generate_openapi.py

compare-openapi:
	uv run python generate_openapi.py --out-destination '.' --out-filename 'openapi_latest.json'
	@if cmp --silent $(CURRENT_OPENAPI) $(LATEST_OPENAPI); then \
		rm $(LATEST_OPENAPI); \
		echo "Swagger file is up to date"; \
	else \
		echo "Swagger files are not equal, did you run 'make pr' or 'make openapi'?"; \
		rm $(LATEST_OPENAPI); \
		exit 1; \
	fi

	# npx cdk deploy --app="${PYTHON} ${PWD}/../infra/app.py" --require-approval=never

# SSM Parameter Setup - creates the Anthropic API key in SSM Parameter Store
# Usage: ANTHROPIC_API_KEY=sk-ant-xxx make ssm-setup
ssm-setup:
	@if [ -z "$(ANTHROPIC_API_KEY)" ]; then \
		echo "Error: ANTHROPIC_API_KEY environment variable not set"; \
		echo "Usage: ANTHROPIC_API_KEY=sk-ant-xxx make ssm-setup"; \
		exit 1; \
	fi
	aws ssm put-parameter \
		--name "/careervp/$${ENVIRONMENT:-dev}/anthropic-api-key" \
		--value "$(ANTHROPIC_API_KEY)" \
		--type SecureString \
		--overwrite \
		--region $${AWS_REGION:-us-east-1}
	@echo "SSM parameter created: /careervp/$${ENVIRONMENT:-dev}/anthropic-api-key"

# Deployment helpers
STACK_NAME := CareerVpCrud$(if $(filter $(ENVIRONMENT),dev staging prod),$(shell echo $(ENVIRONMENT) | tr '[:lower:]' '[:upper:]' | sed 's/PROD/PRODUCTION/'))

cleanup-changesets:
	@echo "Checking for stuck changesets on $(STACK_NAME)..."
	@CHANGESETS=$(shell aws cloudformation list-change-sets \
		--stack-name "$(STACK_NAME)" \
		--query "Summaries[?Status==\`CREATE_IN_PROGRESS\` || Status==\`FAILED\`].ChangeSetName" \
		--output text 2>/dev/null || echo ""); \
	if [ -n "$$CHANGESETS" ]; then \
		echo "Found stuck changesets, cleaning up..."; \
		echo "$$CHANGESETS" | tr '\t' '\n' | while read changeset; do \
			if [ -n "$$changeset" ]; then \
				echo "  Deleting: $$changeset"; \
				aws cloudformation delete-change-set \
					--stack-name "$(STACK_NAME)" \
					--change-set-name "$$changeset" 2>/dev/null || true; \
			done; \
	else \
		echo "No stuck changesets found."; \
	fi

wait-for-stack:
	@STATUS=$(shell aws cloudformation describe-stacks \
		--stack-name "$(STACK_NAME)" \
		--query "Stacks[0].StackStatus" \
		--output text 2>/dev/null || echo "NOT_FOUND"); \
	echo "Stack status: $$STATUS"; \
	case "$$STATUS" in \
		*CREATE_IN_PROGRESS*|*UPDATE_IN_PROGRESS*) \
			echo "Waiting for stack completion..."; \
			aws cloudformation wait stack-create-complete --stack-name "$(STACK_NAME)" 2>/dev/null || \
			aws cloudformation wait stack-update-complete --stack-name "$(STACK_NAME)" 2>/dev/null || true; \
			;; \
		*FAILED*|*ROLLBACK*) \
			echo "Stack is in failed state ($$STATUS), deleting for clean deploy..."; \
			aws cloudformation delete-stack --stack-name "$(STACK_NAME)"; \
			echo "Waiting for stack deletion..."; \
			aws cloudformation wait stack-delete-complete --stack-name "$(STACK_NAME)" || true; \
			;; \
	esac

# Post-deploy smoke test - verifies Lambda functions can call Anthropic API
smoke-test:
	@echo "Running smoke test..."
	$(eval API_URL := $(shell aws cloudformation describe-stacks \
		--stack-name CareerVpCrudDev \
		--query "Stacks[0].Outputs[?OutputKey=='Apigateway'].OutputValue" \
		--output text \
		--region $${AWS_REGION:-us-east-1}))
	@echo "API Gateway URL: $(API_URL)"
	@echo "Testing swagger endpoint..."
	curl -sf "$(API_URL)swagger" > /dev/null && echo "Swagger endpoint OK" || echo "Swagger endpoint failed"
	@echo "Testing VPR endpoint (expects 400 for missing data, proves Lambda runs)..."
	@curl -s -o /dev/null -w "%{http_code}" -X POST "$(API_URL)api/vpr" \
		-H "Content-Type: application/json" \
		-d '{}' | grep -q "4[0-9][0-9]\|5[0-9][0-9]" && echo "VPR Lambda responding" || echo "VPR Lambda not responding"
	@echo "Smoke test complete"
	@if [ -f "tests/aws_cli_smoke.sh" ]; then \
		echo "Running AWS CLI smoke tests..."; \
		bash tests/aws_cli_smoke.sh; \
	else \
		echo "AWS CLI smoke test script not found, skipping."; \
	fi
