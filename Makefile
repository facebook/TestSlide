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
SRCS = testslide util pytest-testslide
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

%_unittest.py: coverage_erase
	@printf "${TERM_BRIGHT}UNITTEST $@\n${TERM_NONE}"
	${Q} coverage run \
		-m unittest \
		${UNITTEST_ARGS} \
		--failfast \
		$@

.PHONY: unittest_tests
unittest_tests: $(TESTS_SRCS)/*_unittest.py

.PHONY: pytest_tests
pytest_tests: export PYTHONPATH=${CURDIR}/pytest-testslide:${CURDIR}
pytest_tests: coverage_erase
	@printf "${TERM_BRIGHT}INSTALL pytest_testslide DEPS ${TERM_NONE}\n"
	${Q} pip install -r pytest-testslide/requirements.txt
	@printf "${TERM_BRIGHT}PYTEST pytest_testslide${TERM_NONE}\n"
	${Q} coverage run \
		-m pytest \
		pytest-testslide/tests

%_testslide.py: coverage_erase
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
	pytest_tests \
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
	${Q} pip install -r requirements-dev.txt

.PHONY: install_deps
install_deps:
	@printf "${TERM_BRIGHT}INSTALL DEPS\n${TERM_NONE}"
	${Q} pip install -r requirements.txt

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

.PHONY: build_dev_container
dev_container: 
	@printf "${TERM_BRIGHT}BUILDING DEV CONTAINER\n${TERM_NONE}"
	${Q} docker build -t testslide-dev .

.PHONY: run_tests_in_container
run_tests_in_container: 
	@printf "${TERM_BRIGHT}RUNNING CI IN DEV CONTAINER\n${TERM_NONE}"
	${Q} docker run testslide-dev

.PHONY: run_dev_container
run_dev_container: build_dev_container
	@printf "${TERM_BRIGHT}STARTING DEV CONTAINER WITH BIND-MOUNTED SOURCES\n${TERM_NONE}"
	@docker run --rm -d --name testslide -v ${CURDIR}/testslide:/code/testslide -v ${CURDIR}/tests:/code/tests testslide-dev bash -c "while true; do sleep 30; done"
	@printf "${TERM_BRIGHT}Container testslide is running.\n${TERM_NONE}"
	@printf "${TERM_BRIGHT}Use make enter_dev_container to exec into it.\n${TERM_NONE}"
	@printf "${TERM_BRIGHT}Use make kill_dev_container to terminate it.\n${TERM_NONE}"

.PHONY: enter_dev_container
enter_dev_container:
	@printf "${TERM_BRIGHT}ENTERING DEV CONTAINER\n${TERM_NONE}"
	@docker exec -it testslide bash


.PHONY: kill_dev_container
kill_dev_container:
	@printf "${TERM_BRIGHT}KILLING DEV CONTAINER\n${TERM_NONE}"
	@docker kill testslide

.PHONY: clean_dev_container
clean_dev_container:
	@printf "${TERM_BRIGHT}KILLING DEV CONTAINER\n${TERM_NONE}"
	@docker kill testslide

.PHONY: ci
ci: \
	install_deps \
	install_build_deps \
	tests \
	coverage_report \
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
