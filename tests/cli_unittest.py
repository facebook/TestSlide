# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import unittest
import sys
from contextlib import contextmanager
from testslide import redirect_stdout, redirect_stderr

if sys.version_info[0] >= 3:
    from unittest.mock import Mock, call, patch
else:
    from mock import Mock, call, patch

from testslide import Context, AggregatedExceptions, reset
from testslide.dsl import context, xcontext, fcontext, before_once
from testslide import cli
import traceback
import io
import os


class SimulatedFailure(Exception):
    def __init__(self, message, second_message):
        """
        This method purposely accepts an extra argument to catch failures when
        reraising exceptions.
        """
        super(SimulatedFailure, self).__init__(message, second_message)
        self.message = message
        self.second_message = second_message

    def __str__(self):
        return "{} {}".format(self.message, self.second_message)


class TestCliBase(unittest.TestCase):
    def _create_contexts(self):
        @context
        def top_context(context):
            @context.example
            def passing_example(self):
                pass

            @context.example
            def failing_example(self):
                raise SimulatedFailure("test failure", "(extra)")

            @context.fexample
            def focused_example(self):
                pass

            @context.xexample
            def skipped_example(self):
                pass

            @context.example
            def unittest_SkipTest(self):
                raise unittest.SkipTest("Skipped with unittest.SkipTest")

            @context.sub_context
            def nested_context(context):
                @context.example
                def passing_nested_example(self):
                    pass

    def setUp(self):
        Context.all_top_level_contexts = []
        self._create_contexts()
        self.captured_stdout = io.StringIO()
        self.captured_stderr = io.StringIO()
        self.argv = []
        super(TestCliBase, self).setUp()

    @contextmanager
    def assert_stdout(self, expected_stdout):
        with redirect_stdout(self.captured_stdout):
            yield
        self.assertEqual(self.captured_stdout.getvalue(), expected_stdout)

    @contextmanager
    def assert_in_stdout(self, expected_stdout):
        with redirect_stdout(self.captured_stdout):
            yield
        self.assertTrue(
            expected_stdout in self.captured_stdout.getvalue(),
            "Expected:\n{}\nin stdout:\n{}".format(
                expected_stdout, self.captured_stdout.getvalue()
            ),
        )

    @contextmanager
    def assert_in_stderr(self, expected_stderr):
        with redirect_stderr(self.captured_stderr):
            yield
        self.assertTrue(
            expected_stderr in self.captured_stderr.getvalue(),
            "Expected:\n{}\nin stderr:\n{}".format(
                expected_stderr, self.captured_stderr.getvalue()
            ),
        )

    def execute(self):
        with patch.object(sys, "exit"):
            cli.Cli(self.argv + [__file__]).run()

    @staticmethod
    def white(text):
        return "\x1b[0m\x1b[1m{}\x1b[0m".format(text)

    @staticmethod
    def green(text):
        return "\x1b[0m\x1b[32m{}\x1b[0m".format(text)

    @staticmethod
    def red(text):
        return "\x1b[0m\x1b[31m{}\x1b[0m".format(text)

    @staticmethod
    def yellow(text):
        return "\x1b[0m\x1b[33m{}\x1b[0m".format(text)

    @staticmethod
    def cyan(text):
        return "\x1b[0m\x1b[36m{}\x1b[0m".format(text)


class TestCliQuiet(TestCliBase):
    def setUp(self):
        super(TestCliQuiet, self).setUp()

        @context
        def quiet(context):
            @context.example
            def passing_verbose(self):
                print("stdout text")
                print("stderr text", file=sys.stderr)

            @context.example
            def failing_verbose(self):
                print("stdout text")
                print("stderr text", file=sys.stderr)
                raise SimulatedFailure("test failure", "(extra)")

            @context.example
            def last_example(self):
                pass

    def test_with_quiet(self):
        """
        With --quiet, swallow both stderr and stdout unless the test fails.
        """
        self.argv.append("--quiet")
        with self.assert_in_stdout(
            "quiet\n"
            "  passing verbose: PASS\n"
            "stdout:\n"
            "stdout text\n"
            "\n"
            "stderr:\n"
            "stderr text\n"
            "\n"
            "  failing verbose: SimulatedFailure: test failure (extra)\n"
            "  last example: PASS\n"
        ):
            self.execute()

    def test_without_quiet(self):
        """
        Without --quiet, allow test stdout and stderr to go on.
        """
        stdout = (
            "quiet\n"
            "stdout text\n"
            "  passing verbose: PASS\n"
            "stdout text\n"
            "  failing verbose: SimulatedFailure: test failure (extra)\n"
            "  last example: PASS\n"
        )
        stderr = "stderr text\nstderr text\n"
        with self.assert_in_stdout(stdout), self.assert_in_stderr(stderr):
            self.execute()


class TestCliDocumentation(TestCliBase):
    def setUp(self):
        TestCliBase.setUp(self)
        self.argv.append("--format")
        self.argv.append("documentation")
        self.maxDiff = None
        self.tb_shared_root = os.getcwd() + os.sep
        self.tb_nested_path = "some/path/"
        self.tb_prefix = "".join([self.tb_shared_root, self.tb_nested_path])
        self.tb_list = [
            ("{}one.py".format(self.tb_prefix), 42, "func1", "doSomething()"),
            ("{}one/two.py".format(self.tb_prefix), 43, "func2", "doOther()"),
        ]
        self.tb_default_trimmed_list = [
            ("{}one.py".format(self.tb_nested_path), 42, "func1", "doSomething()"),
            ("{}one/two.py".format(self.tb_nested_path), 43, "func2", "doOther()"),
        ]
        self.tb_custom_trimmed_list = [
            ("one.py", 42, "func1", "doSomething()"),
            ("one/two.py", 43, "func2", "doOther()"),
        ]

    def test_colored_output_to_terminal(self):
        """
        Execute all examples in the order defined with colored output.
        """
        with patch.object(self.captured_stdout, "isatty"):
            with self.assert_in_stdout(
                self.white("top context")
                + "\n"
                + self.green("  passing example")
                + "\n"
                + self.red("  failing example: SimulatedFailure: test failure (extra)")
                + "\n"
                + self.green("  *focused example")
                + "\n"
                + self.yellow("  skipped example")
                + "\n"
                + self.yellow("  unittest SkipTest")
                + "\n"
                + self.white("  nested context")
                + "\n"
                + self.green("    passing nested example")
                + "\n"
                # TODO rest of output
            ):
                self.execute()

    def test_colored_output_with_force_color(self):
        """
        Execute all examples in the order defined with colored output.
        """
        self.argv.append("--force-color")
        with self.assert_in_stdout(
            self.white("top context")
            + "\n"
            + self.green("  passing example")
            + "\n"
            + self.red("  failing example: SimulatedFailure: test failure (extra)")
            + "\n"
            + self.green("  *focused example")
            + "\n"
            + self.yellow("  skipped example")
            + "\n"
            + self.yellow("  unittest SkipTest")
            + "\n"
            + self.white("  nested context")
            + "\n"
            + self.green("    passing nested example")
            + "\n"
            # TODO rest of output
        ):
            self.execute()

    def test_plain_output_without_terminal(self):
        """
        Execute all examples in the order defined without color.
        """
        with self.assert_in_stdout(
            "top context\n"
            "  passing example: PASS\n"
            "  failing example: SimulatedFailure: test failure (extra)\n"
            "  *focused example: PASS\n"
            "  skipped example: SKIP\n"
            "  unittest SkipTest: SKIP\n"
            "  nested context\n"
            "    passing nested example: PASS\n"
            # TODO rest of output
        ):
            self.execute()

    def test_shuffle(self):
        """
        Shuffle execution order.
        """
        self.argv.append("--shuffle")
        self.argv.append("--seed")
        self.argv.append("33")
        if sys.version_info[0] >= 3:
            expected_stdout = "top context\n"
            "  skipped example: SKIP\n"
            "  passing example: PASS\n"
            "  *focused example: PASS\n"
            "  failing example: FAIL: SimulatedFailure: test failure (extra)\n"
            "  nested context\n"
            "    passing nested example: PASS\n\n"
        else:
            expected_stdout = "top context\n"
            "  failing example: FAIL: SimulatedFailure: test failure (extra)\n"
            "  passing example: PASS\n"
            "  skipped example: SKIP\n"
            "  nested context\n"
            "    passing nested example: PASS\n"
            "  *focused example: PASS\n\n"

        with self.assert_in_stdout(
            expected_stdout
            # TODO rest of output
        ):
            self.execute()

    def test_focus(self):
        """
        Execute only focused examples.
        """
        self.argv.append("--focus")
        with self.assert_in_stdout(
            "top context\n"
            "  *focused example: PASS\n\n"
            # TODO rest of output
        ):
            self.execute()

    def test_fail_fast(self):
        """
        Stop execution when first example fails.
        """
        self.argv.append("--fail-fast")
        with self.assert_in_stdout(
            "top context\n"
            "  passing example: PASS\n"
            "  failing example: SimulatedFailure: test failure (extra)\n\n"
            # TODO rest of output
        ):
            self.execute()

    def test_text_filter(self):
        """
        Execute only examples matching partial text filter.
        """
        self.argv.append("--filter-text")
        self.argv.append("nested context: passing nested ex")
        with self.assert_in_stdout(
            "top context\n"
            "  nested context\n"
            "    passing nested example: PASS\n\n"
            # TODO rest of output
        ):
            self.execute()

    def test_regexp_filter(self):
        """
        Execute only examples matching partial text filter.
        """
        self.argv.append("--filter-regex")
        self.argv.append(".*passing nested.*")
        with self.assert_in_stdout(
            "top context\n"
            "  nested context\n"
            "    passing nested example: PASS\n\n"
            # TODO rest of output
        ):
            self.execute()

    def test_default_trim_stack_trace_path_prefix(self):
        """
        Default value for --trim-stack-trace-path-prefix trims path shared with
        testslide itself.
        """
        with patch.object(traceback, "extract_tb", return_value=self.tb_list):
            with self.assert_in_stdout(
                "".join(
                    '      File "{}", line {}, in {}\n        {}\n'.format(
                        path, line, func, code
                    )
                    for path, line, func, code in self.tb_default_trimmed_list
                )
            ):
                self.execute()

    def test_nonempty_trim_stack_trace_path_prefix(self):
        """
        Trims prefix passed to --trim-stack-trace-path-prefix.
        """
        self.argv.append("--trim-stack-trace-path-prefix")
        self.argv.append(self.tb_prefix)
        with patch.object(traceback, "extract_tb", return_value=self.tb_list):
            with self.assert_in_stdout(
                "".join(
                    '      File "{}", line {}, in {}\n        {}\n'.format(
                        path, line, func, code
                    )
                    for path, line, func, code in self.tb_custom_trimmed_list
                )
            ):
                self.execute()

    def test_empty_trim_strace_path_prefix(self):
        """
        Trims nothing if '' passed to --trim-stack-trace-path-prefix.
        """
        self.argv.append("--trim-stack-trace-path-prefix")
        self.argv.append("")
        with patch.object(traceback, "extract_tb", return_value=self.tb_list):
            with self.assert_in_stdout(
                "".join(
                    '      File "{}", line {}, in {}\n        {}\n'.format(
                        path, line, func, code
                    )
                    for path, line, func, code in self.tb_list
                )
            ):
                self.execute()


class TestCliProgress(TestCliBase):
    def setUp(self):
        TestCliBase.setUp(self)
        self.argv.append("--format")
        self.argv.append("progress")

    def test_ouputs_dots(self):
        with self.assert_stdout(".F.SS.\n"):
            self.execute()

    def test_ouputs_colored_dots_with_terminal(self):
        with patch.object(self.captured_stdout, "isatty"):
            with self.assert_stdout(
                self.green(".")
                + self.red("F")
                + self.green(".")
                + self.yellow("S")
                + self.yellow("S")
                + self.green(".")
                + "\n"
            ):
                self.execute()
