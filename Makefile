# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

##
## Variables
##

TESTSLIDE_FORMAT?=documentation
UNITTEST_VERBOSE?=--verbose
TESTS_SRCS = tests
SRCS = testslide
ALL_SRCS = $(TESTS_SRCS) $(SRCS)

##
## Default
##

.PHONY: all
all: all_tests

##
## Rules
##

%_unittest.py: FORCE
	coverage run -m unittest $(UNITTEST_VERBOSE) --failfast $@

%_testslide.py: FORCE
	coverage run -m testslide.cli --format $(TESTSLIDE_FORMAT) --show-testslide-stack-trace --fail-fast --fail-if-focused $@

# .PHONY does not work for implicit rules, so we FORCE them
FORCE:

##
## Docs
##

.PHONY: docs
docs:
	cd docs && make html

.PHONY: docs_clean
docs_clean:
	rm -rf docs/_build/

##
## Tests
##

.PHONY: unittest_tests
unittest_tests: $(TESTS_SRCS)/*_unittest.py

.PHONY: testslide_tests
testslide_tests: $(TESTS_SRCS)/*_testslide.py

.PHONY: mypy
mypy:
	mypy testslide

.PHONY: flake8
flake8:
	flake8 --select=F,C90 $(ALL_SRCS)

.PHONY: black_check
black_check:
	black --check $(ALL_SRCS)

.PHONY: coverage_tests
coverage_tests: unittest_tests testslide_tests

.PHONY: all_tests
all_tests: \
	coverage_tests \
	mypy \
	flake8 \
	black_check
##
## Coverage
##

.PHONY: coverage_erase
coverage_erase:
	coverage erase

.PHONY: coverage_combine
coverage_combine: coverage_erase coverage_tests
	coverage combine

.PHONY: coverage_report
coverage_report: coverage_combine
	coverage report

.PHONY: coverage_html
coverage_html: coverage_combine
	coverage html

.PHONY: coverage_html_clean
coverage_html_clean:
	rm -rf htmlcov/

.PHONY: coveralls
coveralls: coverage_combine
	coveralls

##
## Build
##

.PHONY: install_build_deps
install_build_deps:
	pip install -e .[test,build]

.PHONY: sdist
sdist:
	python setup.py sdist

.PHONY: sdist_clean
sdist_clean:
	rm -rf dist/ MANIFEST TestSlide.egg-info/

.PHONY: install_local
install_local:
	pip install -e .
	testslide --help

.PHONY: travis
travis: \
	install_build_deps \
	all_tests \
	coverage_report \
	coveralls \
	docs \
	sdist \
	install_local

##
## Clean
##

.PHONY: clean
clean: sdist_clean docs_clean coverage_html_clean coverage_erase
	rm -rf */__pycache__/ */*.pyc