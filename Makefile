BUMP_LEVEL := patch

login:
	@aws codeartifact login --tool pip --repository ceti --domain ceti-repo

login_twine:
	@aws codeartifact login --tool twine --repository ceti --domain ceti-repo

clean:
	@python setup.py clean --all
	@rm -rf ./dist ./*egg-info

build_tools:
	@pip install --upgrade pip build bumpversion twine virtualenv

build: clean
	@python -m build --sdist --wheel --outdir dist/ .

bumpversion:
	@bump2version ${BUMP_LEVEL}

release: bumpversion
	@git push origin main --tags

publish: build_tools build login_twine
	@python -m twine upload --repository codeartifact dist/ceti-*

# LocalStack testing targets
localstack-up:
	@echo "Starting LocalStack..."
	@docker-compose -f docker-compose.localstack.yml up -d 2>&1
	@echo "Waiting for LocalStack to be ready..."
	@sleep 5
	@echo "LocalStack is ready at http://localhost:4566"

localstack-down:
	@echo "Stopping LocalStack..."
	@docker-compose -f docker-compose.localstack.yml down
	@echo "LocalStack stopped"

localstack-clean:
	@echo "Cleaning LocalStack data..."
	@docker-compose -f docker-compose.localstack.yml down -v
	@echo "LocalStack data cleaned"

localstack-logs:
	@docker-compose -f docker-compose.localstack.yml logs -f

test-local: localstack-up
	@echo "Running tests with LocalStack..."
	@set -a && . $(CURDIR)/.env.localstack && set +a && pytest -v
	@echo "Stopping LocalStack..."
	@docker-compose -f docker-compose.localstack.yml down 2>&1
	@echo "LocalStack stopped"

.PHONY: login login_twine clean build_tools build bumpversion release publish \
        localstack-up localstack-down localstack-clean localstack-logs test-local
