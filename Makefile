collectstatic:
	mkdir -p dockci/static/lib/css
	mkdir -p dockci/static/lib/fonts
	mkdir -p dockci/static/lib/js

htmldeps:
	npm install
	node_modules/bower/bin/bower --allow-root install
pythondeps:
	python3.4 -m virtualenv -p $(shell which python3.4) python_env
	python_env/bin/pip install -r requirements.txt
testdeps:
	python_env/bin/pip install -r test-requirements.txt
deps: htmldeps pythondeps collectstatic

styletest:  # don't install deps
	python_env/bin/pep8 dockci
	python_env/bin/pylint --rcfile pylint.conf dockci
unittest: export PYTHONPATH = $(shell pwd)
unittest:
	python_env/bin/py.test -vv tests
test: testdeps styletest unittest

# Container commands
ci: test
migrate:
	@python_env/bin/python -m dockci.migrations.run
run: migrate
	@python_env/bin/gunicorn --workers 20 --timeout 0 --bind 0.0.0.0:5000 --preload wsgi
sh:
	@sh

.PHONY: ci collectstatic htmldeps pythondeps testdeps deps run styletest test
