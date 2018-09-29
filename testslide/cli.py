# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import argparse
import os
import re
import json
from time import time
import sys
from six import StringIO
from . import redirect_stdout, redirect_stderr
import traceback

from . import Context, AggregatedExceptions, Skip
from .runner import Runner, ProgressFormatter, DocumentFormatter
import unittest
import testslide.dsl

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

        test_methods = [
            getattr(test_case, test_method_name)
            for test_method_name in dir(test_case)
            if test_method_name.startswith("test")
            or test_method_name.startswith("ftest")
            or test_method_name.startswith("xtest")
            # FIXME: debug why ismethod is not properly filtering methods. Using
            # callabdle as a workaround.
            # if inspect.ismethod(getattr(test_case, test_method_name))
            if callable(getattr(test_case, test_method_name))
        ]

        if not test_methods:
            continue

        # This extra method is needed so context_code is evaluated with different
        # values of test_case.
        def get_context_code(test_case):
            def context_code(test_case_context):

                test_case_context.merge_test_case(test_case, "test_case")

                for test_method in test_methods:

                    # Same trick as above.
                    def gen_example_code(test_method):
                        def example_code(self):
                            test_method(self.test_case)

                        return example_code

                    example_name = test_method.__name__
                    # Regular example
                    if test_method.__name__.startswith("test"):
                        test_case_context.example(example_name)(
                            gen_example_code(test_method)
                        )
                    # Focused example
                    if test_method.__name__.startswith("ftest"):
                        test_case_context.fexample(example_name)(
                            gen_example_code(test_method)
                        )
                    # Skipped example
                    if test_method.__name__.startswith("xtest"):
                        test_case_context.xexample(example_name)(
                            gen_example_code(test_method)
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

    def _build_parser(self):
        parser = argparse.ArgumentParser(description="TestSlide")
        parser.add_argument(
            "-f",
            "--format",
            choices=["p", "progress", "d", "documentation"],
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
            "--quiet",
            action="store_true",
            help="Suppress output (stdout and stderr) of tested code",
        )
        default_trim_strace_path_prefix = os.getcwd() + os.sep
        parser.add_argument(
            "--trim-strace-path-prefix",
            nargs=1,
            type=str,
            default=[default_trim_strace_path_prefix],
            help=(
                "Remove the specified prefix from stack trace paths in the output. "
                "Default: {}".format(repr(default_trim_strace_path_prefix))
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

    def __init__(self, args):
        self.args = args
        self.parser = self._build_parser()

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
        config.trim_strace_path_prefix = parsed_args.trim_strace_path_prefix[0]
        config.shuffle = parsed_args.shuffle
        config.seed = parsed_args.seed[0] if parsed_args.seed else None
        config.focus = parsed_args.focus
        config.fail_fast = parsed_args.fail_fast
        config.names_text_filter = (
            parsed_args.filter_text[0] if parsed_args.filter_text else None
        )
        config.names_regex_filter = (
            parsed_args.filter_regex[0] if parsed_args.filter_regex else None
        )
        config.quiet = parsed_args.quiet
        config.import_module_names = [
            _filename_to_module_name(test_file) for test_file in parsed_args.test_files
        ]

        return config

    def run(self):
        try:
            config = self._get_config_from_parsed_args(
                self.parser.parse_args(self.args)
            )
        except SystemExit as e:
            if e.code > 0:
                # FIXME find a better way to exit without ignoring other exit
                # hooks
                os._exit(e.code)
            else:
                return

        if config.profile_threshold_ms is not None:
            import_secs = self._do_imports(
                config.import_module_names, config.profile_threshold_ms
            )
        else:
            import_secs = self._load_all_examples(config.import_module_names)
        exit_code = Runner(
            Context.all_top_level_contexts,
            self.FORMAT_NAME_TO_FORMATTER_CLASS[config.format](
                force_color=config.force_color,
                import_secs=import_secs,
                trim_strace_path_prefix=config.trim_strace_path_prefix,
            ),
            shuffle=config.shuffle,
            seed=config.seed,
            focus=config.focus,
            fail_fast=config.fail_fast,
            names_text_filter=config.names_text_filter,
            names_regex_filter=config.names_regex_filter,
            quiet=config.quiet,
        ).run()
        sys.exit(exit_code)


def main():
    # We need to make sure current directory is at sys.path, to allow relative module imports.
    if not "" in sys.path:
        sys.path.insert(0, "")
    Cli(sys.argv[1:]).run()


if __name__ == "__main__":
    main()
