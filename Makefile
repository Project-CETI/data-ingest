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

# Whale Tag Simulator targets
whaletag-up:
	@echo "Starting whale tag simulator..."
	@set -a && . $(CURDIR)/.env.whaletag && set +a && docker-compose -f docker-compose.whaletag.yml up -d 2>&1
	@echo "Waiting for SSH server to start..."
	@sleep 3
	@echo ""
	@echo "Whale tag simulator is ready!"
	@echo "  Container: $${WHALETAG_HOSTNAME:-wt-b827eb123456}"
	@echo "  Hostname: $${WHALETAG_HOSTNAME:-wt-b827eb123456}"
	@echo "  SSH Port: 22"
	@echo "  SSH User: pi"
	@echo "  SSH Password: $${WHALETAG_PASSWORD:-ceticeti}"
	@echo ""
	@echo "Get container IP:"
	@echo "  docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' $${WHALETAG_HOSTNAME:-wt-b827eb123456}"
	@echo ""
	@echo "Test connection:"
	@echo "  ssh pi@$$(docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' $${WHALETAG_HOSTNAME:-wt-b827eb123456})"

whaletag-down:
	@echo "Stopping whale tag simulator..."
	@docker-compose -f docker-compose.whaletag.yml down 2>&1
	@echo "Whale tag simulator stopped"

whaletag-clean:
	@echo "Cleaning whale tag data..."
	@docker-compose -f docker-compose.whaletag.yml down -v 2>&1
	@echo "Whale tag data cleaned"

test-whaletag:
	@echo "Testing whale tag simulator..."
	@$(MAKE) whaletag-up
	@echo "Running whale tag tests..."
	@pytest -m whaletag -v || ($(MAKE) whaletag-down && exit 1)
	@$(MAKE) whaletag-down
	@echo "Whale tag tests completed"
