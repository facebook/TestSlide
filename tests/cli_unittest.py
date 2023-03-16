# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import os
import os.path
import pty
import re
import subprocess
import sys
import threading
import unittest

import testslide


class TestCliBase(unittest.TestCase):
    SAMPLE_TESTS_PATH = os.path.dirname(__file__) + "/sample_tests.py"

    def setUp(self):
        self.argv = [self.SAMPLE_TESTS_PATH]
        self.env = {
            "COVERAGE_PROCESS_START": ".coveragerc",
        }
        super(TestCliBase, self).setUp()

    def run_testslide(
        self,
        tty_stdout=False,
        expected_return_code=0,
        expected_stdout=None,
        expected_stdout_startswith=None,
        expected_in_stdout=None,
        expected_not_in_stdout=None,
        expected_regex_in_stdout=None,
        show_testslide_stack_trace=True,
    ):
        args = [
            sys.executable,
            "-m",
            "testslide.cli",
        ]
        if show_testslide_stack_trace:
            args.append("--show-testslide-stack-trace")
        args.extend(self.argv)

        env = dict(os.environ)
        env.update(self.env)

        if tty_stdout:
            stdout_master_fd, stdout_slave_fd = pty.openpty()

        encoding = sys.getdefaultencoding()

        with subprocess.Popen(
            args,
            bufsize=1,
            stdin=subprocess.DEVNULL,
            stdout=stdout_slave_fd if tty_stdout else subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding=encoding,
            env=env,
            universal_newlines=True,
        ) as popen:
            stdout_chunks = []
            stderr_chunks = []

            def _process_output(fd, callback):
                while True:
                    try:
                        chunk = os.read(fd, 8192)
                    except OSError:
                        break
                    if len(chunk):
                        callback(chunk)
                    else:
                        break

            if tty_stdout:
                stdout_fileno = stdout_master_fd
            else:
                stdout_fileno = popen.stdout.fileno()

            process_stdout_thread = threading.Thread(
                target=_process_output,
                name="process_stdout",
                args=(stdout_fileno, lambda line: stdout_chunks.append(line)),
            )
            process_stdout_thread.start()

            process_stderr_thread = threading.Thread(
                target=_process_output,
                name="process_stderr",
                args=(popen.stderr.fileno(), lambda line: stderr_chunks.append(line)),
            )
            process_stderr_thread.start()

            return_code = popen.wait()
            if tty_stdout:
                os.close(stdout_slave_fd)
            process_stdout_thread.join()
            process_stderr_thread.join()

        stdout_output = "".join(chunk.decode(encoding) for chunk in stdout_chunks)
        stderr_output = "".join(chunk.decode(encoding) for chunk in stderr_chunks)
        output = ""
        if stdout_output:
            output += f"STDOUT:\n{stdout_output}\n"
        if stderr_output:
            output += f"STDERR:\n{stderr_output}\n"
        self.assertEqual(
            return_code,
            expected_return_code,
            f"Command {args} returned {return_code}, "
            f"expected {expected_return_code}.\n{output}",
        )
        if expected_stdout:
            self.assertEqual(
                stdout_output,
                expected_stdout,
                f"Command {args} expected to have have this stdout:\n\n"
                f"{expected_stdout}\n\n"
                f"But output was different:\n"
                f"{stdout_output}",
            )
        if expected_stdout_startswith:
            self.assertTrue(
                stdout_output.startswith(expected_stdout_startswith),
                f"Command {args} expected to have have its stdout starting with:\n\n"
                f"{expected_stdout_startswith}\n\n"
                f"But output was different:\n"
                f"{stdout_output}",
            )
        if expected_in_stdout:
            self.assertTrue(
                expected_in_stdout in stdout_output,
                f"Command {args} expected to have have in its stdout:\n\n"
                f"{expected_in_stdout}\n\n"
                f"But output was different:\n"
                f"{stdout_output}",
            )
        if expected_not_in_stdout:
            self.assertTrue(
                expected_not_in_stdout not in stdout_output,
                f"Command {args} expected to not have have in its stdout:\n\n"
                f"{expected_not_in_stdout}\n\n"
                f"But output was different:\n"
                f"{stdout_output}",
            )
        if expected_regex_in_stdout:
            self.assertTrue(
                re.fullmatch(expected_regex_in_stdout, stdout_output, flags=re.DOTALL),
                f"Command {args} expected to have have its stdout matching the regexp:\n\n"
                f"{expected_regex_in_stdout}\n\n"
                f"But output was different:\n"
                f"{stdout_output}",
            )

    @staticmethod
    def bright(text):
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


class TestCliList(TestCliBase):
    def setUp(self):
        super().setUp()
        self.argv.insert(0, "--list")

    def test_list(self):
        """
        With --list, print test names one per line.
        """
        self.run_testslide(
            expected_stdout=(
                "top context: passing example\n"
                "top context: failing example\n"
                "top context: focused example\n"
                "top context: skipped example\n"
                "top context: unittest SkipTest\n"
                "top context, nested context: passing nested example\n"
                "tests.sample_tests.SampleTestCase: test_failing\n"
                "tests.sample_tests.SampleTestCase: test_passing\n"
                "tests.sample_tests.SampleTestCase: test_skipped\n"
            )
        )


class TestCliQuiet(TestCliBase):
    def setUp(self):
        super().setUp()
        self.env = {"PRINT": "True"}

    def test_with_quiet(self):
        """
        With --quiet, swallow both stderr and stdout unless the test fails.
        """
        self.argv.insert(0, "--quiet")
        self.run_testslide(
            expected_return_code=1,
            expected_stdout_startswith=(
                "top context\n"
                "  passing example: PASS\n"
                "stdout:\n"
                "failing_example stdout\n"
                "\n"
                "stderr:\n"
                "failing_example stderr\n"
                "\n"
                "  failing example: SimulatedFailure: test failure (extra)\n"
                "  *focused example: PASS\n"
                "  skipped example: SKIP\n"
                "  unittest SkipTest: SKIP\n"
                "  nested context\n"
                "    passing nested example: PASS\n"
                "tests.sample_tests.SampleTestCase\n"
                "stdout:\n"
                "test_fail stdout\n"
                "\n"
                "stderr:\n"
                "test_fail stderr\n"
                "\n"
                "  test_failing: AssertionError: Third\n"
                "  test_passing: PASS\n"
                "  test_skipped: SKIP\n"
                "\n"
                "Failures:\n"
                # TODO Rest of the output
            ),
        )

    def test_without_quiet(self):
        """
        Without --quiet, allow test stdout and stderr to go on.
        """
        self.run_testslide(
            expected_return_code=1,
            expected_stdout_startswith=(
                "top context\n"
                "passing_example stdout\n"
                "  passing example: PASS\n"
                "failing_example stdout\n"
                "  failing example: SimulatedFailure: test failure (extra)\n"
                "focused_example stdout\n"
                "  *focused example: PASS\n"
                "  skipped example: SKIP\n"
                "unittest_SkipTest stdout\n"
                "  unittest SkipTest: SKIP\n"
                "  nested context\n"
                "passing_nested_example stdout\n"
                "    passing nested example: PASS\n"
                "tests.sample_tests.SampleTestCase\n"
                "test_fail stdout\n"
                "  test_failing: AssertionError: Third\n"
                "test_pass stdout\n"
                "  test_passing: PASS\n"
                "  test_skipped: SKIP\n"
                "\n"
                "Failures:\n"
                # TODO Rest of the output
            ),
        )


class FormatterMixin:
    def test_prints_exceptions_with_cause(self):
        self.run_testslide(
            tty_stdout=True,
            expected_return_code=1,
            expected_in_stdout=(
                '      File \x1b[36m"tests/sample_tests.py"\x1b[39;49;00m, line \x1b[94m76\x1b[39;49;00m, in test_failing\x1b[37m\x1b[39;49;00m\r\n'
                '    \x1b[37m    \x1b[39;49;00m\x1b[94mraise\x1b[39;49;00m \x1b[36mAssertionError\x1b[39;49;00m(\x1b[33m"\x1b[39;49;00m\x1b[33mThird\x1b[39;49;00m\x1b[33m"\x1b[39;49;00m) \x1b[94mfrom\x1b[39;49;00m \x1b[04m\x1b[36mcause\x1b[39;49;00m\x1b[37m\x1b[39;49;00m\r\n'
                "\x1b[0m\x1b[31m      Caused by \x1b[0m\x1b[0m\x1b[31mAssertionError: Second\x1b[0m\r\n"
                '        File \x1b[36m"tests/sample_tests.py"\x1b[39;49;00m, line \x1b[94m74\x1b[39;49;00m, in test_failing\x1b[37m\x1b[39;49;00m\r\n'
                '      \x1b[37m    \x1b[39;49;00m\x1b[94mraise\x1b[39;49;00m \x1b[36mAssertionError\x1b[39;49;00m(\x1b[33m"\x1b[39;49;00m\x1b[33mSecond\x1b[39;49;00m\x1b[33m"\x1b[39;49;00m) \x1b[94mfrom\x1b[39;49;00m \x1b[04m\x1b[36mcause\x1b[39;49;00m\x1b[37m\x1b[39;49;00m\r\n'
                "\x1b[0m\x1b[31m        Caused by \x1b[0m\x1b[0m\x1b[31mAssertionError: First\x1b[0m\r\n"
                '          File \x1b[36m"tests/sample_tests.py"\x1b[39;49;00m, line \x1b[94m72\x1b[39;49;00m, in test_failing\x1b[37m\x1b[39;49;00m\r\n'
                '        \x1b[37m    \x1b[39;49;00m\x1b[94mraise\x1b[39;49;00m \x1b[36mAssertionError\x1b[39;49;00m(\x1b[33m"\x1b[39;49;00m\x1b[33mFirst\x1b[39;49;00m\x1b[33m"\x1b[39;49;00m)\x1b[37m\x1b[39;49;00m\r\n'
            ),
        )

    def test_default_trim_path_prefix(self):
        """
        Default value for --trim-path-prefix trims path shared with
        testslide itself.
        """
        self.run_testslide(
            expected_return_code=1,
            expected_in_stdout=('File "tests/sample_tests.py", line'),
        )

    def test_nonempty_trim_path_prefix(self):
        """
        Trims prefix passed to --trim-path-prefix.
        """
        self.argv.append("--trim-path-prefix")
        self.argv.append(os.path.dirname(self.SAMPLE_TESTS_PATH) + "/")
        self.run_testslide(
            expected_return_code=1,
            expected_in_stdout=(
                'File "' + os.path.basename(self.SAMPLE_TESTS_PATH) + '", line'
            ),
        )

    def test_empty_trim_path_prefix(self):
        """
        Trims nothing if '' passed to --trim-path-prefix.
        """
        self.argv.append("--trim-path-prefix")
        self.argv.append("")
        self.run_testslide(
            expected_return_code=1,
            expected_in_stdout=('File "' + self.SAMPLE_TESTS_PATH + '", line'),
        )

    def test_not_show_testslide_stack_trace(self):
        self.run_testslide(
            expected_return_code=1,
            show_testslide_stack_trace=False,
            expected_not_in_stdout=os.path.abspath(os.path.dirname(testslide.__file__)),
        )


class TestCliDocumentFormatter(FormatterMixin, TestCliBase):
    def setUp(self):
        super().setUp()
        self.argv = ["--format", "documentation"] + self.argv

    def test_colored_output_to_terminal(self):
        """
        Execute all examples in the order defined with colored output.
        """
        self.run_testslide(
            tty_stdout=True,
            expected_return_code=1,
            expected_stdout_startswith=(
                self.bright("top context")
                + "\r\n"
                + self.green("  passing example")
                + "\r\n"
                + self.red("  failing example: SimulatedFailure: test failure (extra)")
                + "\r\n"
                + self.green("  *focused example")
                + "\r\n"
                + self.yellow("  skipped example")
                + "\r\n"
                + self.yellow("  unittest SkipTest")
                + "\r\n"
                + self.bright("  nested context")
                + "\r\n"
                + self.green("    passing nested example")
                + "\r\n"
                # TODO Rest of the output
            ),
        )

    def test_colored_output_with_force_color(self):
        """
        Execute all examples in the order defined with colored output.
        """
        self.argv.append("--force-color")

        self.run_testslide(
            expected_return_code=1,
            expected_stdout_startswith=(
                self.bright("top context")
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
                + self.bright("  nested context")
                + "\n"
                + self.green("    passing nested example")
                + "\n"
                # TODO add remaining bits of the output (using regexes)
            ),
        )

    def test_plain_output_without_terminal(self):
        """
        Execute all examples in the order defined without color.
        """
        self.run_testslide(
            expected_return_code=1,
            expected_stdout_startswith=(
                "top context\n"
                "  passing example: PASS\n"
                "  failing example: SimulatedFailure: test failure (extra)\n"
                "  *focused example: PASS\n"
                "  skipped example: SKIP\n"
                "  unittest SkipTest: SKIP\n"
                "  nested context\n"
                "    passing nested example: PASS\n"
                "tests.sample_tests.SampleTestCase\n"
                "  test_failing: AssertionError: Third\n"
                "  test_passing: PASS\n"
                "  test_skipped: SKIP\n"
                "\n"
                "Failures:\n"
                # TODO add remaining bits of the output (using regexes)
            ),
        )

    def test_shuffle(self):
        """
        Shuffle execution order.
        """
        self.argv.append("--shuffle")
        self.argv.append("--seed")
        self.argv.append("33")
        self.run_testslide(
            expected_return_code=1,
            expected_stdout_startswith=(
                "top context\n"
                "  passing example: PASS\n"
                "  unittest SkipTest: SKIP\n"
                "  nested context\n"
                "    passing nested example: PASS\n"
                "  failing example: SimulatedFailure: test failure (extra)\n"
                "tests.sample_tests.SampleTestCase\n"
                "  test_passing: PASS\n"
                "  test_skipped: SKIP\n"
                "  test_failing: AssertionError: Third\n"
                "top context\n"
                "  skipped example: SKIP\n"
                "  *focused example: PASS\n"
                "\n"
                "Failures:\n"
                # TODO add remaining bits of the output (using regexes)
            ),
        )

    def test_focus(self):
        """
        Execute only focused examples.
        """
        self.argv.append("--focus")
        self.run_testslide(
            expected_stdout_startswith=(
                "top context\n"
                "  *focused example: PASS\n"
                # TODO add remaining bits of the output (using regexes)
            )
        )

    def test_fail_if_focus(self):
        """
        Fail because there are focused tests and --fail-if-focused
        """
        self.argv.append("--fail-if-focused")
        self.run_testslide(
            expected_return_code=1,
            expected_stdout_startswith=(
                "top context\n"
                "  passing example: PASS\n"
                "  failing example: SimulatedFailure: test failure (extra)\n"
                "  *focused example: AssertionError: Focused example not allowed with --fail-if-focused. Please remove the focus to allow the test to run.\n"
                "  skipped example: SKIP\n"
                "  unittest SkipTest: SKIP\n"
                "  nested context\n"
                "    passing nested example: PASS\n"
                "tests.sample_tests.SampleTestCase\n"
                "  test_failing: AssertionError: Third\n"
                "  test_passing: PASS\n"
                "  test_skipped: SKIP\n"
                "\n"
                "Failures:\n"
            ),
        )

    def test_fail_fast(self):
        """
        Stop execution when first example fails.
        """
        self.argv.append("--fail-fast")
        self.run_testslide(
            expected_return_code=1,
            expected_stdout_startswith=(
                "top context\n"
                "  passing example: PASS\n"
                "  failing example: SimulatedFailure: test failure (extra)\n"
                "\n"
                "Failures:\n"
            ),
        )

    def test_text_filter(self):
        """
        Execute only examples matching partial text filter.
        """
        self.argv.append("--filter-text")
        self.argv.append("nested context: passing nested ex")

        self.run_testslide(
            expected_return_code=0,
            expected_stdout_startswith=(
                "top context\n"
                "  nested context\n"
                "    passing nested example: PASS\n"
            ),
        )

    def test_regexp_filter(self):
        """
        Execute only examples matching regex filter.
        """
        self.argv.append("--filter-regex")
        self.argv.append(".*passing nested.*")
        self.run_testslide(
            expected_return_code=0,
            expected_stdout_startswith=(
                "top context\n"
                "  nested context\n"
                "    passing nested example: PASS\n"
            ),
        )

    def test_exclude_regexp(self):
        """
        Skip examples matching regex filter.
        """
        self.argv.append("--exclude-regex")
        self.argv.append(".*failing.*")
        self.run_testslide(
            expected_return_code=0,
            expected_stdout_startswith=(
                "top context\n"
                "  passing example: PASS\n"
                "  *focused example: PASS\n"
                "  skipped example: SKIP\n"
                "  unittest SkipTest: SKIP\n"
                "  nested context\n"
                "    passing nested example: PASS\n"
                "tests.sample_tests.SampleTestCase\n"
                "  test_passing: PASS\n"
                "  test_skipped: SKIP\n"
            ),
        )

    def test_dsl_debug(self):
        self.argv.append("--dsl-debug")
        self.run_testslide(
            expected_return_code=1,
            expected_regex_in_stdout=(
                "top context\n"
                r"  example: passing_example @ tests/sample_tests.py:\d+\n"
                "  passing example: PASS\n"
                r"  example: failing_example @ tests/sample_tests.py:\d+\n"
                r"  failing example: SimulatedFailure: test failure \(extra\)\n"
                r"  example: focused_example @ tests/sample_tests.py:\d+\n"
                r"  \*focused example: PASS\n"
                "  skipped example: SKIP\n"
                r"  example: unittest_SkipTest @ tests/sample_tests.py:\d+\n"
                "  unittest SkipTest: SKIP\n"
                "  nested context\n"
                r"    example: passing_nested_example @ tests/sample_tests.py:\d+\n"
                "    passing nested example: PASS\n"
                "tests.sample_tests.SampleTestCase\n"
                "  test_failing: AssertionError: Third\n"
                "  test_passing: PASS\n"
                "  test_skipped: SKIP\n"
                ".*"
            ),
        )


class TestCliProgressFormatter(FormatterMixin, TestCliBase):
    def setUp(self):
        super().setUp()
        self.argv.append("--format")
        self.argv.append("progress")

    def test_ouputs_dots(self):
        self.run_testslide(
            expected_return_code=1,
            expected_stdout_startswith=(".F.SS.F.S" + "\nFailures:"),
        )

    def test_ouputs_colored_dots_with_terminal(self):
        self.maxDiff = None
        self.run_testslide(
            tty_stdout=True,
            expected_return_code=1,
            expected_stdout_startswith=(
                self.green(".")
                + self.red("F")
                + self.green(".")
                + self.yellow("S")
                + self.yellow("S")
                + self.green(".")
                + self.red("F")
                + self.green(".")
                + self.yellow("S")
                + self.red("\r\nFailures:")
            ),
        )

    def test_dsl_debug(self):
        self.argv.append("--dsl-debug")
        self.run_testslide(
            expected_return_code=1,
            expected_regex_in_stdout=(
                "\n"
                r"example: passing_example @ tests/sample_tests.py:\d+\n"
                ".\n"
                r"example: failing_example @ tests/sample_tests.py:\d+\n"
                "F\n"
                r"example: focused_example @ tests/sample_tests.py:\d+\n"
                ".\n"
                "S\n"
                r"example: unittest_SkipTest @ tests/sample_tests.py:\d+\n"
                "S\n"
                r"example: passing_nested_example @ tests/sample_tests.py:\d+\n"
                ".\n"
                "F\n"
                ".\n"
                "S\n"
            ),
        )


class TestCliLongFormatter(FormatterMixin, TestCliBase):
    def setUp(self):
        super().setUp()
        self.argv = ["--format", "long"] + self.argv

    def test_colored_output_to_terminal(self):
        """
        Execute all examples in the order defined with colored output.
        """
        self.run_testslide(
            tty_stdout=True,
            expected_return_code=1,
            expected_stdout_startswith=(
                self.bright("top context: ")
                + self.green("passing example")
                + "\r\n"
                + self.bright("top context: ")
                + self.red("failing example: SimulatedFailure: test failure (extra)")
                + "\r\n"
                + self.bright("top context: ")
                + self.green("*focused example")
                + "\r\n"
                + self.bright("top context: ")
                + self.yellow("skipped example")
                + "\r\n"
                + self.bright("top context: ")
                + self.yellow("unittest SkipTest")
                + "\r\n"
                + self.bright("top context, nested context: ")
                + self.green("passing nested example")
                + "\r\n"
                + self.bright("tests.sample_tests.SampleTestCase: ")
                + self.red("test_failing: AssertionError: Third")
                + "\r\n"
                + self.bright("tests.sample_tests.SampleTestCase: ")
                + self.green("test_passing")
                + "\r\n"
                + self.bright("tests.sample_tests.SampleTestCase: ")
                + self.yellow("test_skipped")
                + "\r\n"
                # TODO Rest of the output
            ),
        )

    def test_colored_output_with_force_color(self):
        """
        Execute all examples in the order defined with colored output.
        """
        self.argv.append("--force-color")

        self.run_testslide(
            expected_return_code=1,
            expected_stdout_startswith=(
                self.bright("top context: ")
                + self.green("passing example")
                + "\n"
                + self.bright("top context: ")
                + self.red("failing example: SimulatedFailure: test failure (extra)")
                + "\n"
                + self.bright("top context: ")
                + self.green("*focused example")
                + "\n"
                + self.bright("top context: ")
                + self.yellow("skipped example")
                + "\n"
                + self.bright("top context: ")
                + self.yellow("unittest SkipTest")
                + "\n"
                + self.bright("top context, nested context: ")
                + self.green("passing nested example")
                + "\n"
                + self.bright("tests.sample_tests.SampleTestCase: ")
                + self.red("test_failing: AssertionError: Third")
                + "\n"
                + self.bright("tests.sample_tests.SampleTestCase: ")
                + self.green("test_passing")
                + "\n"
                + self.bright("tests.sample_tests.SampleTestCase: ")
                + self.yellow("test_skipped")
                + "\n"
                # TODO Rest of the output
            ),
        )

    def test_plain_output_without_terminal(self):
        """
        Execute all examples in the order defined without color.
        """
        self.run_testslide(
            expected_return_code=1,
            expected_stdout_startswith=(
                "top context: passing example: PASS\n"
                "top context: failing example: SimulatedFailure: test failure (extra)\n"
                "top context: *focused example: PASS\n"
                "top context: skipped example: SKIP\n"
                "top context: unittest SkipTest: SKIP\n"
                "top context, nested context: passing nested example: PASS\n"
                "tests.sample_tests.SampleTestCase: test_failing: AssertionError: Third\n"
                "tests.sample_tests.SampleTestCase: test_passing: PASS\n"
                "tests.sample_tests.SampleTestCase: test_skipped: SKIP\n"
                # TODO add remaining bits of the output (using regexes)
            ),
        )

    def test_dsl_debug(self):
        self.argv.append("--dsl-debug")
        self.run_testslide(
            expected_return_code=1,
            expected_regex_in_stdout=(
                "top context: \n"
                r"  example: passing_example @ tests/sample_tests.py:\d+\n"
                "  passing example: PASS\n"
                "top context: \n"
                r"  example: failing_example @ tests/sample_tests.py:\d+\n"
                r"  failing example: SimulatedFailure: test failure \(extra\)\n"
                "top context: \n"
                r"  example: focused_example @ tests/sample_tests.py:\d+\n"
                r"  \*focused example: PASS\n"
                "top context: \n"
                "  skipped example: SKIP\n"
                "top context: \n"
                r"  example: unittest_SkipTest @ tests/sample_tests.py:\d+\n"
                "  unittest SkipTest: SKIP\n"
                "top context, nested context: \n"
                r"  example: passing_nested_example @ tests/sample_tests.py:\d+\n"
                "  passing nested example: PASS\n"
                "tests.sample_tests.SampleTestCase: \n"
                "  test_failing: AssertionError: Third\n"
                "tests.sample_tests.SampleTestCase: \n"
                "  test_passing: PASS\n"
                "tests.sample_tests.SampleTestCase: \n"
                "  test_skipped: SKIP\n"
                ".*"
            ),
        )
