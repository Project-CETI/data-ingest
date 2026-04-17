BUMP_LEVEL := patch

install:
	pip install -e .[test]

test:
	pytest -v

whaletag-up:
	docker compose up -d --build whaletag-mock
	@echo ""
	@echo "Whale tag mock is running. Get its IP with:"
	@echo "  docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' wt-b827eb123456"
	@echo ""
	@echo "Or connect via localhost:2222:"
	@echo "  ssh pi@localhost -p 2222   (password: ceticeti)"

whaletag-down:
	docker compose down

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
