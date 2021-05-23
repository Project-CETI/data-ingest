clean:
	@python setup.py clean --all
	@rm -rf ./dist ./*egg-info

build_tools:
	@pip install --upgrade pip setuptools wheel

build: clean
	@python setup.py sdist bdist_wheel
