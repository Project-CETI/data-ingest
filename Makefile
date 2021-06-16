BUMP_LEVEL := patch

clean:
	@python setup.py clean --all
	@rm -rf ./dist ./*egg-info

build_tools:
	@pip install --upgrade pip build

build: clean
	@python -m build --sdist --wheel --outdir dist/ .

bumpversion:
	@bump2version ${BUMP_LEVEL}

release: bumpversion, build
