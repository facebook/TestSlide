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

# Verbose output: make V=1
V?=0
ifeq ($(V),0)
Q := @python silent_if_successful.py
else
Q := 
endif

##
## Default
##

.PHONY: all
all: all_tests

# .PHONY does not work for implicit rules, so we FORCE them
FORCE:

##
## Docs
##

.PHONY: docs
docs:
	@printf "DOCS\n"
	${Q} make -C docs/ html

.PHONY: docs_clean
docs_clean:
	@printf "DOCS CLEAN\n"
	${Q} rm -rf docs/_build/

##
## Tests
##

%_unittest.py: FORCE
	@printf "UNITTEST $@\n"
	${Q} coverage run \
		-m unittest \
		$(UNITTEST_VERBOSE) \
		--failfast \
		$@

.PHONY: unittest_tests
unittest_tests: $(TESTS_SRCS)/*_unittest.py

%_testslide.py: FORCE
	@printf "TESTSLIDE $@\n"
	${Q} coverage run \
		-m testslide.cli \
		--format $(TESTSLIDE_FORMAT) \
		--show-testslide-stack-trace \
		--fail-fast \
		--fail-if-focused \
		$@

.PHONY: testslide_tests
testslide_tests: $(TESTS_SRCS)/*_testslide.py

.PHONY: mypy
mypy:
	@printf "MYPY ${ALL_SRCS}\n"
	${Q} mypy ${ALL_SRCS}

.PHONY: flake8
flake8:
	@printf "FLAKE8 ${ALL_SRCS}\n"
	${Q} flake8 --select=F,C90 $(ALL_SRCS)

.PHONY: black_check
black_check:
	@printf "BLACK ${ALL_SRCS}\n"
	${Q} black --check $(ALL_SRCS)

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
	@printf "COVERAGE ERASE\n"
	${Q} coverage erase

.PHONY: coverage_combine
coverage_combine: coverage_erase coverage_tests
	@printf "COVERAGE COMBINE\n"
	${Q} coverage combine

.PHONY: coverage_report
coverage_report: coverage_combine
	@printf "COVERAGE REPORT\n"
	${Q} coverage report

.PHONY: coverage_html
coverage_html: coverage_combine
	@printf "COVERAGE HTML\n"
	${Q} coverage html

.PHONY: coverage_html_clean
coverage_html_clean:
	@printf "COVERAGE HTML CLEAN\n"
	${Q} rm -rf htmlcov/

.PHONY: coveralls
coveralls: coverage_combine
	@printf "COVERALLS\n"
	${Q} coveralls

##
## Build
##

.PHONY: install_build_deps
install_build_deps:
	@printf "INSTALL BUILD DEPS\n"
	${Q} pip install -e .[test,build]

.PHONY: sdist
sdist:
	@printf "SDIST\n"
	${Q} python setup.py sdist

.PHONY: sdist_clean
sdist_clean:
	@printf "SDIST CLEAN\n"
	${Q} rm -rf dist/ MANIFEST TestSlide.egg-info/

.PHONY: install_local
install_local:
	@printf "INSTALL LOCAL\n"
	${Q} pip install -e .
	${Q} testslide --help

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
	@printf "CLEAN\n"
	${Q} rm -rf */__pycache__/ */*.pyc