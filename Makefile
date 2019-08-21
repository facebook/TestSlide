# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

.PHONY: all
all: test

.PHONY: flake8
flake8:
	flake8 --select=F,C90 testslide/ tests/

.PHONY: black_check
black_check:
	bash -c "if black --help &>/dev/null ; then exec black --check testslide/ tests/ ; fi"

.PHONY: unittest_tests
unittest_tests:
	python -m unittest discover --verbose --failfast -p '*_unittest.py'

.PHONY: testslide_tests
testslide_tests:
	python -m testslide.cli --show-testslide-stack-trace --fail-fast --fail-if-focused tests/*_testslide.py

.PHONY: docs
docs:
	cd docs && if python -c 'import sys ; sys.exit(1 if sys.version.startswith("2.") else 0)' ; then make html ; fi

.PHONY: sdist
sdist:
	python setup.py sdist

.PHONY: test
test: unittest_tests testslide_tests black_check flake8 docs sdist

.PHONY: install_deps
install_deps:
	pip install -e .[test,build]

.PHONY: clean
clean:
	rm -rf dist/ MANIFEST TestSlide.egg-info/ */__pycache__/ */*.pyc docs/_build/
