# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

##
## Variables
##

TESTSLIDE_FORMAT?=documentation
UNITTEST_VERBOSE?=1
ifeq ($(UNITTEST_VERBOSE),0)
UNITTEST_ARGS :=
else
UNITTEST_ARGS := --verbose
endif
TESTS_SRCS = tests
SRCS = testslide util
ALL_SRCS = $(TESTS_SRCS) $(SRCS)
TERM_BRIGHT := $(shell tput bold)
TERM_NONE := $(shell tput sgr0)
DIST_TAR_GZ = dist/TestSlide-$(shell cat testslide/version).tar.gz

# Verbose output: make V=1
V?=0
ifeq ($(V),0)
Q := @python3 util/run_silent_if_successful.py
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

.PHONY: mypy_clean
mypy_clean:
	@printf "${TERM_BRIGHT}MYPY CLEAN\n${TERM_NONE}"
	${Q} rm -rf .mypy_cache/

.PHONY: flake8
flake8:
	@printf "${TERM_BRIGHT}FLAKE8 ${ALL_SRCS}\n${TERM_NONE}"
	${Q} flake8 --select=F,C90 $(ALL_SRCS)

.PHONY: black
black:
	@printf "${TERM_BRIGHT}BLACK ${ALL_SRCS}\n${TERM_NONE}"
	${Q} black --check $(ALL_SRCS) || { echo "Formatting errors found, try running 'make format'."; exit 1; }

.PHONY: isort
isort:
	@printf "${TERM_BRIGHT}ISORT ${ALL_SRCS}\n${TERM_NONE}"
	${Q} isort --check-only --profile black $(ALL_SRCS) || { echo "Formatting errors found, try running 'make format'."; exit 1; }

.PHONY: format_isort
format_isort:
	@printf "${TERM_BRIGHT}FORMAT PYFMT ${ALL_SRCS}\n${TERM_NONE}"
	${Q} isort --profile black $(ALL_SRCS)

.PHONY: format_black
format_black:
	@printf "${TERM_BRIGHT}FORMAT BLACK ${ALL_SRCS}\n${TERM_NONE}"
	${Q} black $(ALL_SRCS)

.PHONY: tests
tests: \
	unittest_tests \
	testslide_tests \
	mypy \
	flake8 \
	isort \
	black

.PHONY: format
format: \
    format_isort \
	format_black

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

.PHONY: twine
twine: sdist
	twine upload $(DIST_TAR_GZ)

.PHONY: install_local
install_local: sdist
	@printf "${TERM_BRIGHT}INSTALL LOCAL\n${TERM_NONE}"
	${Q} pip install $(DIST_TAR_GZ)
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
clean: sdist_clean docs_clean coverage_html_clean coverage_erase mypy_clean
	@printf "${TERM_BRIGHT}CLEAN\n${TERM_NONE}"
	${Q} rm -rf */__pycache__/ */*.pyc
