htmldeps:
	npm install
	node_modules/bower/bin/bower install
pythondeps:
	pip install -r requirements.txt
deps: htmldeps pythondeps

styletest:  # don't install deps
	pep8 *.py
	pylint --rcfile pylint.conf *.py
test: styletest

# Container commands
ci: test
run:
	@python3 /code/main.py
sh:
	@sh

.PHONY: ci htmldeps pythondeps deps run styletest test
