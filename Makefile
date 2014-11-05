htmldeps:
	npm install
	node_modules/bower/bin/bower --allow-root install
pythondeps:
	pip3 install -r requirements.txt
deps: htmldeps pythondeps

styletest:  # don't install deps
	pep8 *.py
	pylint --rcfile pylint.conf *.py
test: styletest

# Container commands
ci: test
run:
	@python3 /code/main.py 0.0.0.0
sh:
	@sh

.PHONY: ci htmldeps pythondeps deps run styletest test
