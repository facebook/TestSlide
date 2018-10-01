# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import random
from time import time
import traceback
import six
import sys
import os

from . import (
    AggregatedExceptions,
    Skip,
    redirect_stdout,
    redirect_stderr,
    _add_traceback_context_manager,
)


class Formatter(object):
    """
    Formatter base class. To be paired with Runner, to process / output example
    execution results.
    """

    def __init__(
        self, force_color=False, import_secs=None, trim_strace_path_prefix=None
    ):
        self.force_color = force_color
        self.import_secs = import_secs
        self._import_secs_warn = True
        self.trim_strace_path_prefix = trim_strace_path_prefix
        self.reset()

    def reset(self):
        """
        To be called before each run.
        """
        self.current_hierarchy = []
        self.results = {"success": [], "fail": [], "skip": []}
        self.start_time = time()
        self.end_time = None
        self.duration_secs = None
        if self.import_secs and self.import_secs > 1 and self._import_secs_warn:
            self.print_yellow(
                "Warning: Importing test modules alone took %.1fs! To remove this slow "
                "down remove object construction from module level. If not possible, "
                "consider using lazy_import(). Try using --import-profiler to profile "
                "your imports." % (self.import_secs)
            )
            self._import_secs_warn = False

    def start(self, example):
        """
        To be called before each example execution.
        """
        context_to_print = [
            context
            for context in example.context.hierarchy
            if context not in self.current_hierarchy
        ]
        for context in context_to_print:
            self.new_context(context)
        self.new_example(example)
        self.current_hierarchy = example.context.hierarchy

    def new_context(self, context):
        """
        Called before an example execution, when its context is different from
        previous executed example.
        """
        pass

    def new_example(self, example):
        """
        Called before an example execution.
        """
        pass

    def success(self, example):
        """
        Called when an example was Successfuly executed.
        """
        self.results["success"].append(example)

    def fail(self, example, exception):
        """
        Called when an example failed on execution.
        """
        self.results["fail"].append({"example": example, "exception": exception})

    def skip(self, example):
        """
        Called when an example had the execution skipped.
        """
        self.results["skip"].append(example)

    def finish(self, not_executed_examples):
        """
        Called when all examples finished execution.
        """
        self.end_time = time()
        self.duration_secs = self.end_time - self.start_time
        pass

    def _print_attrs(self, attrs, *values, **kwargs):
        stream = kwargs.get("file", sys.stdout)
        if stream.isatty() or self.force_color:
            print(
                "\033[0m\033[{attrs}m{value}\033[0m".format(
                    attrs=attrs, value="".join([str(value) for value in values])
                ),
                **kwargs
            )
        else:
            if sys.version_info[0] >= 3:
                print(*values, **kwargs)
            else:
                print(*[unicode(v) for v in values], **kwargs)  # noqa: F821

    def print_white(self, *values, **kwargs):
        self._print_attrs("1", *values, **kwargs)

    def print_green(self, *values, **kwargs):
        self._print_attrs("32", *values, **kwargs)

    def print_red(self, *values, **kwargs):
        self._print_attrs("31", *values, **kwargs)

    def print_yellow(self, *values, **kwargs):
        self._print_attrs("33", *values, **kwargs)

    def print_cyan(self, *values, **kwargs):
        self._print_attrs("36", *values, **kwargs)


class ProgressFormatter(Formatter):
    """
    Simple formatter that outputs "." when an example passes or "F" w
    """

    def success(self, example):
        Formatter.success(self, example)
        self.print_green(".", end="")

    def fail(self, example, exception):
        Formatter.fail(self, example, exception)
        self.print_red("F", end="")

    def skip(self, example):
        Formatter.skip(self, example)
        self.print_yellow("S", end="")

    def finish(self, not_executed_examples):
        Formatter.finish(self, not_executed_examples)
        print("")


class DocumentFormatter(Formatter):
    def new_context(self, context):
        self.print_white(
            "{}{}{}".format("  " * context.depth, "*" if context.focus else "", context)
        )

    def _color_output(self):
        return sys.stdout.isatty() or self.force_color

    def success(self, example):
        Formatter.success(self, example)
        self.print_green(
            "{indent}{focus}{example}{pass_text}".format(
                indent="  " * (example.context.depth + 1),
                focus="*" if example.focus else "",
                example=example,
                pass_text="" if self._color_output() else ": PASS",
            )
        )

    def fail(self, example, exception):
        if isinstance(exception, AggregatedExceptions) and 1 == len(
            exception.exceptions
        ):
            exception = exception.exceptions[0]

        Formatter.fail(self, example, exception)

        self.print_red(
            "{indent}{focus}{example}: {ex_class}: {ex_message}".format(
                indent="  " * (example.context.depth + 1),
                focus="*" if example.focus else "",
                example=example,
                ex_class=type(exception).__name__,
                ex_message=str(exception).split("\n")[0],
            )
        )

    def skip(self, example):
        Formatter.skip(self, example)
        self.print_yellow(
            "{indent}{focus}{example}{skip_text}".format(
                indent="  " * (example.context.depth + 1),
                focus="*" if example.focus else "",
                example=example,
                skip_text="" if self._color_output() else ": SKIP",
            )
        )

    def print_failed_example(self, number, example, exception):
        self.print_white(
            "  {number}) {context}: {example}".format(
                number=number, context=example.context.full_name, example=example
            )
        )
        if type(exception) is AggregatedExceptions:
            exception_list = exception.exceptions
        else:
            exception_list = [exception]
        for number, exception in enumerate(exception_list):
            self.print_red(
                "    {number}) {exception_class}: {message}".format(
                    number=number + 1,
                    exception_class=exception.__class__.__name__,
                    message="\n    ".join(str(exception).split("\n")),
                )
            )
            for path, line, function_name, text in traceback.extract_tb(
                exception.__traceback__
            ):
                # Hide TestSlide's steps of the stack
                if path.startswith(os.path.dirname(__file__)):
                    continue
                if self.trim_strace_path_prefix:
                    split = path.split(self.trim_strace_path_prefix)
                    if len(split) == 2 and not split[0]:
                        path = split[1]
                self.print_cyan(
                    '      File "{}", line {}, in {}\n'
                    "        {}".format(path, line, function_name, text)
                )

    def finish(self, not_executed_examples):
        Formatter.finish(self, not_executed_examples)
        success = len(self.results["success"])
        fail = len(self.results["fail"])
        skip = len(self.results["skip"])
        total = success + fail + skip
        if self.results["fail"]:
            self.print_red("\nFailures:")
            for number, result in enumerate(self.results["fail"]):
                print("")
                self.print_failed_example(
                    number + 1, result["example"], result["exception"]
                )
        print("")
        self.print_white(
            "Finished %s example(s) in %.1fs:" % (total, self.duration_secs)
        )
        if success:
            self.print_green("  Successful: ", success)
        if fail:
            self.print_red("  Failed: ", fail)
        if skip:
            self.print_yellow("  Skipped: ", skip)
        if not_executed_examples:
            self.print_cyan("  Not executed: ", len(not_executed_examples))


class Runner(object):
    """
    Execute examples contained in given contexts.
    """

    def __init__(
        self,
        contexts,
        formatter,
        shuffle=False,
        seed=None,
        focus=False,
        fail_fast=False,
        names_text_filter=None,
        names_regex_filter=None,
        quiet=False,
    ):
        self.contexts = contexts
        self.formatter = formatter
        self.shuffle = shuffle
        self.seed = seed
        self.focus = focus
        self.fail_fast = fail_fast
        self.names_text_filter = names_text_filter
        self.names_regex_filter = names_regex_filter
        self.quiet = quiet

    def _run_example(self, example):
        if self.quiet:
            stdout = six.StringIO()
            stderr = six.StringIO()
            example_exception = None
            with redirect_stdout(stdout), redirect_stderr(stderr):
                try:
                    with _add_traceback_context_manager():
                        example()
                except BaseException as ex:
                    example_exception = ex
            if example_exception:
                if not isinstance(example_exception, Skip):
                    if stdout.getvalue():
                        print("stdout:\n{}".format(stdout.getvalue()))
                    if stderr.getvalue():
                        print("stderr:\n{}".format(stderr.getvalue()))
                raise example_exception
        else:
            example()

    def run(self):
        """
        Execute all examples in all contexts.
        """
        sys.stdout.flush()
        sys.stderr.flush()
        self.formatter.reset()
        executed_examples = []
        exit_code = 0
        for example in self._to_execute_examples:
            executed_examples.append(example)
            self.formatter.start(example)
            sys.stdout.flush()
            sys.stderr.flush()
            try:
                self._run_example(example)
            except Skip:
                self.formatter.skip(example)
            except BaseException as exception:
                self.formatter.fail(example, exception)
                exit_code = 1
                if self.fail_fast:
                    break
            else:
                self.formatter.success(example)
        not_executed_examples = [
            example
            for example in self._all_examples
            if example not in executed_examples
        ]
        self.formatter.finish(not_executed_examples)
        sys.stdout.flush()
        sys.stderr.flush()
        return exit_code

    def _filter(self, example, focus):
        if focus and not example.focus:
            return False

        if self.names_text_filter:
            if self.names_text_filter not in example.full_name:
                return False

        if self.names_regex_filter:
            if not self.names_regex_filter.match(example.full_name):
                return False

        return True

    @property
    def _all_examples(self):
        examples = [
            example for context in self.contexts for example in context.all_examples
        ]
        if self.shuffle:
            if self.seed:
                random.seed(self.seed)
            random.shuffle(examples)
        return examples

    @property
    def _to_execute_examples(self):
        examples = [
            example
            for example in self._all_examples
            if self._filter(example, focus=self.focus)
        ]
        if not examples and self.focus:
            return [
                example
                for example in self._all_examples
                if self._filter(example, focus=False)
            ]
        return examples
