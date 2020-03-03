# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import argparse
import os
import re
from time import time
import sys

from contextlib import contextmanager

from . import _TestSlideTestResult, Context
from .runner import Runner, ProgressFormatter, DocumentFormatter
import unittest
import testslide.dsl
from .strict_mock import StrictMock

_unittest_testcase_loaded = False


def _filename_to_module_name(name):
    if not (
        os.path.isfile(name)
        and (name.lower().endswith(".py") or name.lower().endswith(".pyc"))
    ):
        raise ValueError("Expected a .py file, got {}".format(name))

    if os.path.isabs(name):
        name = os.path.relpath(name, os.getcwd())
    if name.lower().endswith(".pyc"):
        end = -4
    else:
        end = -3
    return name[:end].replace(os.path.sep, ".")


def _get_all_test_case_subclasses():
    def get_all_subclasses(base):
        return {
            "{}.{}".format(c.__module__, c.__name__): c
            for c in (
                base.__subclasses__()
                + [g for s in base.__subclasses__() for g in get_all_subclasses(s)]
            )
        }.values()

    return get_all_subclasses(unittest.TestCase)


def _get_all_test_cases(import_module_names):
    if import_module_names:
        return [
            test_case
            for test_case in _get_all_test_case_subclasses()
            if test_case.__module__ in import_module_names
        ]
    else:
        return _get_all_test_case_subclasses()


def _load_unittest_test_cases(import_module_names):
    """
    Beta!
    Search for all unittest.TestCase classes that have tests defined, and import them
    as TestSlide contexts and examples. This is useful if you mix unittest.TestCase
    tests and TestSlide at the same file, or if you want to just use TestSlide's test
    runner for existing unittest.TestCase tests.
    """
    global _unittest_testcase_loaded
    if _unittest_testcase_loaded:
        return
    _unittest_testcase_loaded = True

    for test_case in _get_all_test_cases(import_module_names):

        test_method_names = [
            test_method_name
            for test_method_name in dir(test_case)
            if test_method_name.startswith("test")
            or test_method_name.startswith("ftest")
            or test_method_name.startswith("xtest")
            # FIXME: debug why ismethod is not properly filtering methods. Using
            # callabdle as a workaround.
            # if inspect.ismethod(getattr(test_case, test_method_name))
            if callable(getattr(test_case, test_method_name))
        ]

        if not test_method_names:
            continue

        # This extra method is needed so context_code is evaluated with different
        # values of test_case.
        def get_context_code(test_case):
            def context_code(context):

                for test_method_name in test_method_names:

                    @contextmanager
                    def test_result():
                        result = _TestSlideTestResult()
                        yield result
                        result.aggregated_exceptions.raise_correct_exception()

                    @contextmanager
                    def setup_and_teardown():
                        test_case.setUpClass()
                        yield
                        test_case.tearDownClass()

                    # Same trick as above.
                    def gen_example_code(test_method_name):
                        def example_code(self):
                            with test_result() as result:
                                with setup_and_teardown():
                                    test_case(methodName=test_method_name)(
                                        result=result
                                    )

                        return example_code

                    # Regular example
                    if test_method_name.startswith("test"):
                        context.example(test_method_name)(
                            gen_example_code(test_method_name)
                        )
                    # Focused example
                    if test_method_name.startswith("ftest"):
                        context.fexample(test_method_name)(
                            gen_example_code(test_method_name)
                        )
                    # Skipped example
                    if test_method_name.startswith("xtest"):
                        context.xexample(test_method_name)(
                            gen_example_code(test_method_name)
                        )

            return context_code

        testslide.dsl.context("{}.{}".format(test_case.__module__, test_case.__name__))(
            get_context_code(test_case)
        )


class _Config(object):
    pass


class Cli(object):

    FORMAT_NAME_TO_FORMATTER_CLASS = {
        "p": ProgressFormatter,
        "progress": ProgressFormatter,
        "d": DocumentFormatter,
        "documentation": DocumentFormatter,
    }

    @staticmethod
    def _regex_type(string):
        return re.compile(string)

    def _build_parser(self, disable_test_files):
        parser = argparse.ArgumentParser(description="TestSlide")
        parser.add_argument(
            "-f",
            "--format",
            choices=self.FORMAT_NAME_TO_FORMATTER_CLASS.keys(),
            default="documentation",
            help="Configure output format. Default: %(default)s",
        )
        parser.add_argument(
            "--force-color",
            action="store_true",
            help="Force color output even without a terminal",
        )
        parser.add_argument(
            "--shuffle", action="store_true", help="Randomize example execution order"
        )
        parser.add_argument(
            "-l", "--list", action="store_true", help="List all tests one per line"
        )
        parser.add_argument(
            "--seed",
            nargs=1,
            type=int,
            help="Positive number to seed shuffled examples",
        )
        parser.add_argument(
            "--focus",
            action="store_true",
            help="Only executed focused examples, or all if none focused",
        )
        parser.add_argument(
            "--fail-if-focused",
            action="store_true",
            help="Raise an error if an example is focused. Useful when running tests in a continuous integration environment.",
        )
        parser.add_argument(
            "--fail-fast",
            action="store_true",
            help="Stop execution when an example fails",
        )
        parser.add_argument(
            "--filter-text",
            nargs=1,
            type=str,
            help="Only execute examples that include given text in their names",
        )
        parser.add_argument(
            "--filter-regex",
            nargs=1,
            type=self._regex_type,
            help="Only execute examples which match given regex",
        )
        parser.add_argument(
            "--exclude-regex",
            nargs=1,
            type=self._regex_type,
            help="Exclude examples which match given regex from being executed",
        )
        parser.add_argument(
            "--quiet",
            action="store_true",
            help="Suppress output (stdout and stderr) of tested code",
        )
        parser.add_argument(
            "--trim-stack-trace-path-prefix",
            nargs=1,
            type=str,
            default=[self._default_trim_stack_trace_path_prefix],
            help=(
                "Remove the specified prefix from stack trace paths in the output. "
                "Default: {}".format(repr(self._default_trim_stack_trace_path_prefix))
            ),
        )
        parser.add_argument(
            "--show-testslide-stack-trace",
            default=False,
            action="store_true",
            help=(
                "TestSlide's own code is trimmed from stack traces by default. "
                "This flags disables that, useful for TestSlide's own development."
            ),
        )
        parser.add_argument(
            "--import-profiler",
            nargs=1,
            type=int,
            default=None,
            help=(
                "Print profiling information slow import time for modules that took "
                "more than the given number of ms to import. Experimental."
            ),
        )
        if not disable_test_files:
            parser.add_argument(
                "test_files",
                nargs="+",
                type=str,
                default=[],
                help=(
                    "List of file paths that contain either unittes.TestCase "
                    "tests and/or TestSlide's DSL tests."
                ),
            )
        return parser

    def __init__(self, args, default_trim_stack_trace_path_prefix=None, modules=None):
        self.args = args
        self._default_trim_stack_trace_path_prefix = (
            default_trim_stack_trace_path_prefix
            if default_trim_stack_trace_path_prefix
            else os.getcwd() + os.sep
        )
        self.parser = self._build_parser(disable_test_files=bool(modules))
        self._modules = modules

    @staticmethod
    def _do_imports(import_module_names, profile_threshold_ms=None):
        def import_all():
            for module_name in import_module_names:
                __import__(module_name, level=0)

        if profile_threshold_ms is not None:
            from testslide.import_profiler import ImportProfiler

            with ImportProfiler() as import_profiler:
                start_time = time()
                import_all()
                end_time = time()

            import_profiler.print_stats(profile_threshold_ms)

        else:
            start_time = time()
            import_all()
            end_time = time()

        return end_time - start_time

    def _load_all_examples(self, import_module_names):
        """
        Import all required modules.
        """
        import_secs = self._do_imports(import_module_names)
        _load_unittest_test_cases(import_module_names)
        return import_secs

    def _get_config_from_parsed_args(self, parsed_args):
        config = _Config()

        config.profile_threshold_ms = (
            parsed_args.import_profiler[0] if parsed_args.import_profiler else None
        )

        config.format = parsed_args.format
        config.force_color = parsed_args.force_color
        config.trim_stack_trace_path_prefix = parsed_args.trim_stack_trace_path_prefix[
            0
        ]
        config.show_testslide_stack_trace = parsed_args.show_testslide_stack_trace
        config.shuffle = parsed_args.shuffle
        config.list = parsed_args.list
        config.seed = parsed_args.seed[0] if parsed_args.seed else None
        config.focus = parsed_args.focus
        config.fail_if_focused = parsed_args.fail_if_focused
        config.fail_fast = parsed_args.fail_fast
        config.names_text_filter = (
            parsed_args.filter_text[0] if parsed_args.filter_text else None
        )
        config.names_regex_filter = (
            parsed_args.filter_regex[0] if parsed_args.filter_regex else None
        )
        config.names_regex_exclude = (
            parsed_args.exclude_regex[0] if parsed_args.exclude_regex else None
        )
        config.quiet = parsed_args.quiet
        if self._modules:
            config.import_module_names = self._modules
        else:
            config.import_module_names = [
                _filename_to_module_name(test_file)
                for test_file in parsed_args.test_files
            ]
        return config

    def run(self):
        try:
            parsed_args = self.parser.parse_args(self.args)
        except SystemExit as e:
            return e.code
        config = self._get_config_from_parsed_args(parsed_args)

        if config.profile_threshold_ms is not None:
            import_secs = self._do_imports(
                config.import_module_names, config.profile_threshold_ms
            )
            return 0
        else:
            import_secs = self._load_all_examples(config.import_module_names)
            formatter = self.FORMAT_NAME_TO_FORMATTER_CLASS[config.format](
                force_color=config.force_color,
                import_secs=import_secs,
                trim_stack_trace_path_prefix=config.trim_stack_trace_path_prefix,
                show_testslide_stack_trace=config.show_testslide_stack_trace,
            )
            StrictMock.TRIM_PATH_PREFIX = config.trim_stack_trace_path_prefix
            if config.list:
                formatter.discovery_start()
                for context in Context.all_top_level_contexts:
                    for example in context.all_examples:
                        formatter.example_discovered(example)
                formatter.discovery_finish()
                return 0
            else:
                return Runner(
                    contexts=Context.all_top_level_contexts,
                    formatter=formatter,
                    shuffle=config.shuffle,
                    seed=config.seed,
                    focus=config.focus,
                    fail_fast=config.fail_fast,
                    fail_if_focused=config.fail_if_focused,
                    names_text_filter=config.names_text_filter,
                    names_regex_filter=config.names_regex_filter,
                    names_regex_exclude=config.names_regex_exclude,
                    quiet=config.quiet,
                ).run()


def main():
    if "" not in sys.path:
        sys.path.insert(0, "")
    sys.exit(Cli(sys.argv[1:]).run())


if __name__ == "__main__":
    main()
