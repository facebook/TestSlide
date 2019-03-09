# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

.PHONY: all
all: test

.PHONY: black_check
black_check:
	if python -c 'import sys; sys.exit(1 if (sys.version_info.major == 3 and sys.version_info.minor <= 6) else 0)' ; then black --check testslide/ tests/ ; fi

.PHONY: unittest_tests
unittest_tests:
	python -m unittest discover --verbose --failfast -p '*_unittest.py'

.PHONY: testslide_tests
testslide_tests:
	python -m testslide.cli --fail-fast tests/*_testslide.py

.PHONY: docs
docs:
	cd docs && if python -c 'import sys ; sys.exit(1 if sys.version.startswith("2.") else 0)' ; then make html ; fi

.PHONY: test
test: black_check unittest_tests testslide_tests docs

install:
	pip install -e .[test,build]
