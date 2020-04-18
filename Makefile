# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

##
## Variables
##

TESTSLIDE_FORMAT?=documentation
UNITTEST_VERBOSE?=0
ifeq ($(UNITTEST_VERBOSE),0)
UNITTEST_ARGS := --verbose
else
UNITTEST_ARGS := 
endif
TESTS_SRCS = tests
SRCS = testslide
ALL_SRCS = $(TESTS_SRCS) $(SRCS)
TERM_BRIGHT := $(shell tput bold)
TERM_NONE := $(shell tput sgr0)

# Verbose output: make V=1
V?=0
ifeq ($(V),0)
Q := @python util/run_silent_if_successful.py
else
Q := 
endif

##
## Default
##

.PHONY: all
all: tests coverage_report docs sdist

# .PHONY does not work for implicit rules, so we FORCE them
FORCE:

##
## Docs
##

.PHONY: docs
docs:
	@printf "${TERM_BRIGHT}DOCS\n${TERM_NONE}"
	${Q} make -C docs/ html

.PHONY: docs_clean
docs_clean:
	@printf "${TERM_BRIGHT}DOCS CLEAN\n${TERM_NONE}"
	${Q} rm -rf docs/_build/

##
## Tests
##

%_unittest.py: FORCE coverage_erase
	@printf "${TERM_BRIGHT}UNITTEST $@\n${TERM_NONE}"
	${Q} coverage run \
		-m unittest \
		${UNITTEST_ARGS} \
		--failfast \
		$@

.PHONY: unittest_tests
unittest_tests: $(TESTS_SRCS)/*_unittest.py

%_testslide.py: FORCE coverage_erase
	@printf "${TERM_BRIGHT}TESTSLIDE $@\n${TERM_NONE}"
	${Q} coverage run \
		-m testslide.cli \
		--format $(TESTSLIDE_FORMAT) \
		--show-testslide-stack-trace \
		--fail-fast \
		--fail-if-focused \
		$@

.PHONY: testslide_tests coverage_erase
testslide_tests: $(TESTS_SRCS)/*_testslide.py

.PHONY: mypy
mypy:
	@printf "${TERM_BRIGHT}MYPY ${ALL_SRCS}\n${TERM_NONE}"
	${Q} mypy ${ALL_SRCS}

.PHONY: flake8
flake8:
	@printf "${TERM_BRIGHT}FLAKE8 ${ALL_SRCS}\n${TERM_NONE}"
	${Q} flake8 --select=F,C90 $(ALL_SRCS)

.PHONY: black
black:
	@printf "${TERM_BRIGHT}BLACK ${ALL_SRCS}\n${TERM_NONE}"
	${Q} black --check $(ALL_SRCS)

.PHONY: tests
tests: \
	unittest_tests \
	testslide_tests \
	mypy \
	flake8 \
	black

##
## Coverage
##

.PHONY: coverage_erase
coverage_erase:
	@printf "${TERM_BRIGHT}COVERAGE ERASE\n${TERM_NONE}"
	${Q} coverage erase

.PHONY: coverage_combine
coverage_combine: unittest_tests testslide_tests
	@printf "${TERM_BRIGHT}COVERAGE COMBINE\n${TERM_NONE}"
	${Q} coverage combine

.PHONY: coverage_report
coverage_report: coverage_combine
	@printf "${TERM_BRIGHT}COVERAGE REPORT\n${TERM_NONE}"
	${Q} coverage report

.PHONY: coverage_html
coverage_html: coverage_combine
	@printf "${TERM_BRIGHT}COVERAGE HTML\n${TERM_NONE}"
	${Q} coverage html

.PHONY: coverage_html_clean
coverage_html_clean:
	@printf "${TERM_BRIGHT}COVERAGE HTML CLEAN\n${TERM_NONE}"
	${Q} rm -rf htmlcov/

.PHONY: coveralls
coveralls: coverage_combine
	@printf "${TERM_BRIGHT}COVERALLS\n${TERM_NONE}"
	${Q} coveralls

##
## Build
##

.PHONY: install_build_deps
install_build_deps:
	@printf "${TERM_BRIGHT}INSTALL BUILD DEPS\n${TERM_NONE}"
	${Q} pip install -e .[test,build]

.PHONY: sdist
sdist:
	@printf "${TERM_BRIGHT}SDIST\n${TERM_NONE}"
	${Q} python setup.py sdist

.PHONY: sdist_clean
sdist_clean:
	@printf "${TERM_BRIGHT}SDIST CLEAN\n${TERM_NONE}"
	${Q} rm -rf dist/ MANIFEST TestSlide.egg-info/

.PHONY: install_local
install_local:
	@printf "${TERM_BRIGHT}INSTALL LOCAL\n${TERM_NONE}"
	${Q} pip install -e .
	${Q} testslide --help

.PHONY: travis
travis: \
	install_build_deps \
	tests \
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
	@printf "${TERM_BRIGHT}CLEAN\n${TERM_NONE}"
	${Q} rm -rf */__pycache__/ */*.pyc