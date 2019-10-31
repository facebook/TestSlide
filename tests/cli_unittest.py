# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import copy
import os
import os.path
import pty
import subprocess
import sys
import threading
import unittest


class TestCliBase(unittest.TestCase):
    SAMPLE_DSL_PATH = os.path.dirname(__file__) + "/sample_dsl.py"

    def setUp(self):
        self.argv = [self.SAMPLE_DSL_PATH]
        self.env = {}
        super(TestCliBase, self).setUp()

    def run_testslide(
        self,
        tty_stdout=False,
        expected_return_code=0,
        expected_stdout=None,
        expected_stdout_startswith=None,
        expected_in_stdout=None,
    ):
        args = [
            sys.executable,
            "-m",
            "testslide.cli",
            "--show-testslide-stack-trace",
        ] + self.argv

        env = dict(copy.copy(os.environ))
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
                f"{output}",
            )
        if expected_stdout_startswith:
            self.assertTrue(
                stdout_output.startswith(expected_stdout_startswith),
                f"Command {args} expected to have have its stdout starting with:\n\n"
                f"{expected_stdout_startswith}\n\n"
                f"But output was different:\n"
                f"{output}",
            )
        if expected_in_stdout:
            self.assertTrue(
                expected_in_stdout in stdout_output,
                f"Command {args} expected to have have in its stdout:\n\n"
                f"{expected_stdout_startswith}\n\n"
                f"But output was different:\n"
                f"{output}",
            )

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
                "\n"
                "Failures:\n"
                # TODO Rest of the output
            ),
        )


class TestCliDocumentation(TestCliBase):
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
                self.white("top context")
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
                + self.white("  nested context")
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
                "\n"
                "Failures:\n"
                # TODO rest of output
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
                "  *focused example: PASS\n"
                "  skipped example: SKIP\n"
                "  nested context\n"
                "    passing nested example: PASS\n"
                "  failing example: SimulatedFailure: test failure (extra)\n"
                "  unittest SkipTest: SKIP\n"
                "\n"
                "Failures:\n"
                # TODO rest of output
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
                "\n"
                "Finished 1 example(s) in "
                # TODO rest of output
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
                "\n"
                "Finished 1 example(s) in "
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
                "\n"
                "Finished 1 example(s) in "
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
                "\n"
                "Finished 5 example(s) in "
            ),
        )

    def test_default_trim_stack_trace_path_prefix(self):
        """
        Default value for --trim-stack-trace-path-prefix trims path shared with
        testslide itself.
        """
        self.run_testslide(
            expected_return_code=1,
            expected_in_stdout=('File "tests/sample_dsl.py", line'),
        )

    def test_nonempty_trim_stack_trace_path_prefix(self):
        """
        Trims prefix passed to --trim-stack-trace-path-prefix.
        """
        self.argv.append("--trim-stack-trace-path-prefix")
        self.argv.append(os.path.dirname(self.SAMPLE_DSL_PATH) + "/")
        self.run_testslide(
            expected_return_code=1,
            expected_in_stdout=(
                'File "' + os.path.basename(self.SAMPLE_DSL_PATH) + '", line'
            ),
        )

    def test_empty_trim_strace_path_prefix(self):
        """
        Trims nothing if '' passed to --trim-stack-trace-path-prefix.
        """
        self.argv.append("--trim-stack-trace-path-prefix")
        self.argv.append("")
        self.run_testslide(
            expected_return_code=1,
            expected_in_stdout=('File "' + self.SAMPLE_DSL_PATH + '", line'),
        )


class TestCliProgress(TestCliBase):
    def setUp(self):
        super().setUp()
        self.argv.append("--format")
        self.argv.append("progress")

    def test_ouputs_dots(self):
        self.run_testslide(expected_return_code=1, expected_stdout=(".F.SS.\n"))

    def test_ouputs_colored_dots_with_terminal(self):
        self.run_testslide(
            tty_stdout=True,
            expected_return_code=1,
            expected_stdout=(
                self.green(".")
                + self.red("F")
                + self.green(".")
                + self.yellow("S")
                + self.yellow("S")
                + self.green(".")
                + "\r\n"
            ),
        )
