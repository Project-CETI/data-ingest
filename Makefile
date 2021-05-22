BUMP_LEVEL := patch

clean:
	@python setup.py clean --all
	@rm -rf ./dist ./*egg-info

build_tools:
	@pip install --upgrade pip setuptools wheel bump2version

build: clean
	@python setup.py sdist bdist_wheel

bumpversion:
	@bump2version ${BUMP_LEVEL}

release: bumpversion, build
