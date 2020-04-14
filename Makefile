# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

TESTSLIDE_FORMAT?=documentation
UNITTEST_VERBOSE?=--verbose

.PHONY: all
all: test

.PHONY: coveralls
coveralls:
	coveralls

.PHONY: travis
travis: test install_local coveralls

.PHONY: install_deps
install_deps:
	pip install -e .[test,build]

.PHONY: flake8
flake8:
	flake8 --select=F,C90 testslide/ tests/

.PHONY: black_check
black_check:
	black --check testslide/ tests/

.PHONY: coverage_erase
coverage_erase:
	coverage erase

.PHONY: unittest_tests
unittest_tests: coverage_erase
	coverage run -m unittest discover $(UNITTEST_VERBOSE) --failfast -p '*_unittest.py'

.PHONY: testslide_tests
testslide_tests: coverage_erase
	coverage run -m testslide.cli --format $(TESTSLIDE_FORMAT) --show-testslide-stack-trace --fail-fast --fail-if-focused tests/*_testslide.py

.PHONY: coverage_combine
coverage_combine: unittest_tests testslide_tests
	coverage combine

.PHONY: coverage_report
coverage_report: coverage_combine
	coverage report

.PHONY: coverage_html
coverage_html: coverage_combine
	coverage html

.PHONY: docs
docs:
	cd docs && make html

.PHONY: sdist
sdist:
	python setup.py sdist

.PHONY: install_local
install_local:
	pip install -e .
	testslide --help

.PHONY: test
test: unittest_tests testslide_tests coverage_report black_check flake8 docs sdist

.PHONY: clean
clean:
	coverage erase
	rm -rf dist/ MANIFEST TestSlide.egg-info/ */__pycache__/ */*.pyc docs/_build/ htmlcov/
