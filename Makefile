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

.PHONY: htmldeps pythondeps deps styletest test
