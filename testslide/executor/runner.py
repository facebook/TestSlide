# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

# pyre-unsafe

import inspect
import io
import os
import os.path
import random
import re
import sys
import traceback
from collections.abc import Callable
from contextlib import redirect_stderr, redirect_stdout
from importlib import import_module
from re import Pattern
from typing import Any, cast, Union

import pygments
import pygments.formatters
import pygments.lexers
from pygments.token import (
    Comment,
    Error,
    Generic,
    Keyword,
    Name,
    Number,
    Operator,
    String,
    Token,
    Whitespace,
)

# pyre-fixme[21]: Could not find name `BaseFormatter` in `testslide.bdd.lib` (stubbed).
# pyre-fixme[21]: Could not find name `Example` in `testslide.bdd.lib` (stubbed).
from testslide.bdd.lib import BaseFormatter, Context, Example

# pyre-fixme[21]: Could not find name `AggregatedExceptions` in
#  `testslide.executor.lib`.
# pyre-fixme[21]: Could not find name `Skip` in `testslide.executor.lib`.
from .lib import _ExampleRunner, AggregatedExceptions, Skip

##
## Base
##
TS_COLORSCHEME = {
    Token: ("", ""),
    Whitespace: ("gray", "brightblack"),
    Comment: ("gray", "brightblack"),
    Comment.Preproc: ("cyan", "brightcyan"),
    Keyword: ("brightblue", "brightblue"),
    Keyword.Type: ("cyan", "brightcyan"),
    Operator.Word: ("magenta", "brightmagenta"),
    Name.Builtin: ("cyan", "brightcyan"),
    Name.Function: ("green", "brightgreen"),
    Name.Namespace: ("_cyan_", "_brightcyan_"),
    Name.Class: ("_green_", "_brightgreen_"),
    Name.Exception: ("cyan", "brightcyan"),
    Name.Decorator: ("brightblack", "gray"),
    Name.Variable: ("red", "brightred"),
    Name.Constant: ("red", "brightred"),
    Name.Attribute: ("cyan", "brightcyan"),
    Name.Tag: ("brightblue", "brightblue"),
    String: ("yellow", "yellow"),
    Number: ("brightblue", "brightblue"),
    Generic.Deleted: ("brightred", "brightred"),
    Generic.Inserted: ("green", "brightgreen"),
    Generic.Heading: ("**", "**"),
    Generic.Subheading: ("*magenta*", "*brightmagenta*"),
    Generic.Prompt: ("**", "**"),
    Generic.Error: ("brightred", "brightred"),
    Error: ("_brightred_", "_brightred_"),
}


##
## Mixins
##


# pyre-fixme[11]: Annotation `BaseFormatter` is not defined as a type.
class ColorFormatterMixin(BaseFormatter):
    @property
    def colored(self) -> bool:
        # pyre-fixme[16]: `ColorFormatterMixin` has no attribute `force_color`.
        return sys.stdout.isatty() or self.force_color

    def remove_terminal_escape(self, text: str) -> str:
        return re.sub("\033\\[[0-9;]+m", "", text)

    def _format_attrs(self, attrs: str, *values: Any) -> str:
        text = "".join([str(value) for value in values])
        if self.colored:
            return f"\033[0m\033[{attrs}m{text}\033[0m"
        else:
            return text

    def _print_attrs(self, attrs: str, *values: Any, **kwargs: Any) -> None:
        file = kwargs.get("file", None)
        if file is not None:
            raise ValueError()
        if self.colored:
            print(
                self._format_attrs(attrs, *values),
                **kwargs,
            )
        else:
            print(*values, **kwargs)

    def format_bright(self, *values: Any) -> str:
        return self._format_attrs("1", *values)

    def print_bright(self, *values: Any, **kwargs: Any) -> None:
        self._print_attrs("1", *values, **kwargs)

    def format_dim(self, *values: Any) -> str:
        return self._format_attrs("2", *values)

    def print_dim(self, *values: Any, **kwargs: Any) -> None:
        self._print_attrs("2", *values, **kwargs)

    def format_green(self, *values: Any) -> str:
        return self._format_attrs("32", *values)

    def print_green(self, *values: Any, **kwargs: Any) -> None:
        self._print_attrs("32", *values, **kwargs)

    def format_red(self, *values: Any) -> str:
        return self._format_attrs("31", *values)

    def print_red(self, *values: Any, **kwargs: Any) -> None:
        self._print_attrs("31", *values, **kwargs)

    def format_yellow(self, *values: Any) -> str:
        return self._format_attrs("33", *values)

    def format_yellow_bright(self, *values: Any) -> str:
        return self._format_attrs("1;33", *values)

    def print_yellow(self, *values: Any, **kwargs: Any) -> None:
        self._print_attrs("33", *values, **kwargs)

    def format_cyan(self, *values: Any) -> str:
        return self._format_attrs("36", *values)

    def print_cyan(self, *values: Any, **kwargs: Any) -> None:
        self._print_attrs("36", *values, **kwargs)

    def format_cyan_dim_underline(self, *values: Any) -> str:
        return self._format_attrs("36;2;4", *values)

    def print_cyan_dim_underline(self, *values: Any, **kwargs: Any) -> None:
        self._print_attrs("36;2;4", *values, **kwargs)


class FailurePrinterMixin(ColorFormatterMixin):
    @property
    def TESTSLIDE_PATH(self) -> str:
        from testslide import __file__

        return os.path.abspath(os.path.dirname(__file__))

    def _get_test_module_index(self, tb: traceback.StackSummary) -> int | None:
        test_module_paths = [
            import_module(import_module_name).__file__
            # pyre-fixme[16]: `FailurePrinterMixin` has no attribute
            #  `import_module_names`.
            for import_module_name in self.import_module_names
        ]

        test_module_index = None
        for index, value in enumerate(tb):
            path = value[0]
            if path in test_module_paths:
                if test_module_index is None or index < test_module_index:
                    test_module_index = index

        return test_module_index

    def _print_stack_trace(self, exception: BaseException, cause_depth: int) -> None:
        indent = "  " * cause_depth
        if cause_depth:
            self.print_red(f"{indent}    Caused by ", end="")

        self.print_red(
            "{exception_class}: {message}".format(
                exception_class=exception.__class__.__name__,
                message=f"\n{indent}    ".join(str(exception).split("\n")),
            )
        )

        tb = traceback.extract_tb(exception.__traceback__)

        test_module_index = self._get_test_module_index(tb)

        for index, (path, line, function_name, text) in enumerate(tb):
            # pyre-fixme[16]: `FailurePrinterMixin` has no attribute
            #  `show_testslide_stack_trace`.
            if not self.show_testslide_stack_trace:
                if test_module_index is not None and index < test_module_index:
                    continue
                if os.path.abspath(path).startswith(self.TESTSLIDE_PATH):
                    continue
            # pyre-fixme[16]: `FailurePrinterMixin` has no attribute `trim_path_prefix`.
            if self.trim_path_prefix:
                split = path.split(self.trim_path_prefix)
                if len(split) == 2 and not split[0]:
                    path = split[1]
            row_text = (
                '  File "{path}", line {line}, in {function_name}\n'
                "    {text}\n".format(
                    path=path,
                    line=line,
                    function_name=function_name,
                    text=text,
                )
            )
            if self.colored:
                row_text = pygments.highlight(
                    row_text,
                    pygments.lexers.PythonTracebackLexer(),
                    pygments.formatters.TerminalFormatter(colorscheme=TS_COLORSCHEME),
                )
            row_text = "\n".join(
                f"{indent}    {line}" for line in row_text.split("\n")[:-1]
            )
            print(row_text)

        if exception.__cause__:
            self._print_stack_trace(exception.__cause__, cause_depth=cause_depth + 1)

    def print_failed_example(
        self,
        number: int,
        # pyre-fixme[11]: Annotation `Example` is not defined as a type.
        example: Example,
        exception: BaseException,
    ) -> None:
        self.print_bright(
            "  {number}) {context}: {example}".format(
                number=number, context=example.context.full_name, example=example
            )
        )
        # pyre-fixme[16]: Module `lib` has no attribute `AggregatedExceptions`.
        if type(exception) is AggregatedExceptions:
            exception_list = exception.exceptions  # type: ignore
        else:
            exception_list = [exception]
        for number, exception in enumerate(exception_list):
            self.print_red(
                "    {number}) ".format(
                    number=number + 1,
                ),
                end="",
            )
            self._print_stack_trace(exception, cause_depth=0)


class SlowImportWarningMixin(ColorFormatterMixin):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        # pyre-fixme[16]: `SlowImportWarningMixin` has no attribute `import_secs`.
        if self.import_secs and self.import_secs > 1 and self._import_secs_warn:
            self.print_yellow(
                "Warning: Importing test modules alone took %.1fs! To speed this up, "
                "remove object construction from module level. If not possible, "
                "consider using lazy_import(). Try using --import-profiler to profile "
                "your imports." % (self.import_secs)
            )
            self._import_secs_warn = False


class DSLDebugMixin:
    def get_dsl_debug_indent(self, example: Example) -> str:
        return ""

    def _dsl_print(self, example: Example, description: str, code: Callable) -> None:
        lineno: str | int
        if not self.dsl_debug:  # type: ignore
            return
        name = code.__name__
        try:
            file = inspect.getsourcefile(code)
        except TypeError:
            try:
                file = inspect.getfile(code)
            except TypeError:
                file = "?"

        if file and (
            file.startswith(os.path.dirname(__file__))
            or "testslide/core/" in file
            or "testslide/bdd/" in file
        ):
            return
        if self.trim_path_prefix:  # type: ignore
            split = file.split(self.trim_path_prefix)  # type: ignore
            if len(split) == 2 and not split[0]:
                file = split[1]
        try:
            _lines, lineno = inspect.getsourcelines(code)
        except OSError:
            lineno = "?"
        self.print_cyan(  # type: ignore
            "{indent}{description}: {name} @ {file_lineno}".format(
                indent=self.get_dsl_debug_indent(example),
                description=description,
                name=name,
                file_lineno=f"{file}:{lineno}",
            )
        )

    def dsl_example(self, example: Example, code: Callable) -> None:
        self._dsl_print(example, "example", code)

    def dsl_before(self, example: Example, code: Callable) -> None:
        self._dsl_print(example, "before", code)

    def dsl_after(self, example: Example, code: Callable) -> None:
        self._dsl_print(example, "after", code)

    def dsl_around(self, example: Example, code: Callable) -> None:
        self._dsl_print(example, "around", code)

    def dsl_memoize(self, example: Example, code: Callable) -> None:
        self._dsl_print(example, "memoize", code)

    def dsl_memoize_before(self, example: Example, code: Callable) -> None:
        self._dsl_print(example, "memoize_before", code)

    def dsl_function(self, example: Example, code: Callable) -> None:
        self._dsl_print(example, "function", code)


class VerboseFinishMixin(ColorFormatterMixin):
    def _ansi_attrs(self, attrs: str, text: str) -> str:
        if self.colored:
            return f"\033[0m\033[{attrs}m{text}\033[0m"
        else:
            return text

    def _bright_attr(self, text: str) -> str:
        return self._ansi_attrs("1", text)

    def _green_bright_attr(self, text: str) -> str:
        return self._ansi_attrs("32;1", text)

    def _red_bright_attr(self, text: str) -> str:
        return self._ansi_attrs("31;1", text)

    def _yellow_bright_attr(self, text: str) -> str:
        return self._ansi_attrs("33;1", text)

    def _get_ascii_logo_lines(self) -> list[str]:
        quote = '"'
        backslash = "\\"
        return f"""
   {self._yellow_bright_attr("--_")} {self._green_bright_attr(f"|{quote}{quote}---__")}
{self._red_bright_attr("|'.")}{self._yellow_bright_attr("|  |")}{self._green_bright_attr("|")}  {self._bright_attr(".")}    {self._green_bright_attr(f"{quote}{quote}{quote}|")}
{self._red_bright_attr("| |")}{self._yellow_bright_attr("|  |")}{self._green_bright_attr("|")} {self._bright_attr(f"/|{backslash}{quote}{quote}-.")}  {self._green_bright_attr("|")}
{self._red_bright_attr("| |")}{self._yellow_bright_attr("|  |")}{self._green_bright_attr("|")}  {self._bright_attr("|    |")}  {self._green_bright_attr("|")}
{self._red_bright_attr("| |")}{self._yellow_bright_attr("|  |")}{self._green_bright_attr("|")}  {self._bright_attr(f"|   {backslash}|/")} {self._green_bright_attr("|")}
{self._red_bright_attr(f"|.{quote}")}{self._yellow_bright_attr("|  |")}{self._green_bright_attr("|")}  {self._bright_attr(f"--{quote}{quote}")} {self._bright_attr("'")}{self._green_bright_attr("__|")}
   {self._yellow_bright_attr(f"--{quote}")} {self._green_bright_attr(f"|__---{quote}{quote}{quote}")}
""".split("\n")[1:8]

    def _get_summary_lines(
        self, total: int, success: int, fail: int, skip: int, not_executed_examples: int
    ) -> list[str]:
        summary_lines: list[str] = []

        # pyre-fixme[16]: `VerboseFinishMixin` has no attribute `import_secs`.
        if self.import_secs and self.import_secs > 2:
            summary_lines.append(
                self.format_yellow_bright("Imports took: %.1fs!" % (self.import_secs))
                + " Profile with "
                + self.format_bright("--import-profiler")
                + "."
            )
        else:
            summary_lines.append("")

        example = "examples" if total > 1 else "example"
        summary_lines.append(
            self.format_bright(
                "Executed %s %s in %.1fs:"
                # pyre-fixme[16]: `VerboseFinishMixin` has no attribute `duration_secs`.
                % (total, example, cast(float, self.duration_secs)),
            )
        )

        if success:
            summary_lines.append(self.format_green("  Successful: ", success))
        else:
            summary_lines.append(self.format_dim("  Successful: ", success))

        if fail:
            summary_lines.append(self.format_red("  Failed: ", fail))
        else:
            summary_lines.append(self.format_dim("  Failed: ", fail))

        if skip:
            summary_lines.append(self.format_yellow("  Skipped: ", skip))
        else:
            summary_lines.append(self.format_dim("  Skipped: ", skip))

        if not_executed_examples:
            summary_lines.append(
                self.format_cyan("  Not executed: ", not_executed_examples)
            )
        else:
            summary_lines.append(
                self.format_dim("  Not executed: ", not_executed_examples)
            )

        summary_lines.append(
            self.format_cyan_dim_underline("https://testslide.readthedocs.io/")
        )

        return summary_lines

    def finish(self, not_executed_examples: list[Example]) -> None:
        # pyre-fixme[16]: `ColorFormatterMixin` has no attribute `finish`.
        super().finish(not_executed_examples)
        # pyre-fixme[16]: `VerboseFinishMixin` has no attribute `results`.
        success = len(self.results["success"])
        fail = len(self.results["fail"])
        skip = len(self.results["skip"])
        total = success + fail + skip
        if self.results["fail"]:
            self.print_red("\nFailures:")
            for number, result in enumerate(self.results["fail"]):
                result = cast(dict[str, Union[Example, BaseException]], result)
                print("")
                self.print_failed_example(  # type: ignore
                    number + 1,
                    result["example"],
                    result["exception"],  # type: ignore
                )

        summary_lines = self._get_summary_lines(
            total, success, fail, skip, len(not_executed_examples)
        )
        max_summary_len = max(
            [len(self.remove_terminal_escape(line)) for line in summary_lines]
        )

        logo_lines = self._get_ascii_logo_lines()
        max_logo_len = max(
            [len(self.remove_terminal_escape(line)) for line in logo_lines]
        )

        try:
            columns, _lines = os.get_terminal_size()
        except OSError:
            columns = 80

        if columns > 80:
            columns = 80

        if max_summary_len + max_logo_len + 1 <= columns:
            logo_start_column = (
                columns - max_summary_len - max_logo_len - 2 + max_summary_len
            )
            for idx in range(len(summary_lines)):
                print(
                    summary_lines[idx],
                    " "
                    * (
                        max_summary_len
                        - len(self.remove_terminal_escape(summary_lines[idx]))
                        + (logo_start_column - max_summary_len)
                    ),
                    end="",
                )
                print(logo_lines[idx])
        else:
            for idx in range(len(summary_lines)):
                print(
                    summary_lines[idx],
                )


##
## Formatters
##


class QuietFormatter(BaseFormatter):
    pass


class ProgressFormatter(DSLDebugMixin, SlowImportWarningMixin, FailurePrinterMixin):
    """
    Simple formatter that outputs "." when an example passes or "F" w
    """

    def new_example(self, example: Example) -> None:
        # pyre-fixme[16]: `DSLDebugMixin` has no attribute `new_example`.
        super().new_example(example)
        # pyre-fixme[16]: `ProgressFormatter` has no attribute `dsl_debug`.
        if self.dsl_debug:
            print("")

    def success(self, example: Example) -> None:
        # pyre-fixme[16]: `DSLDebugMixin` has no attribute `success`.
        super().success(example)
        self.print_green(".", end="")

    def fail(self, example: Example, exception: BaseException) -> None:
        # pyre-fixme[16]: `DSLDebugMixin` has no attribute `fail`.
        super().fail(example, exception)
        self.print_red("F", end="")

    def skip(self, example: Example) -> None:
        # pyre-fixme[16]: `DSLDebugMixin` has no attribute `skip`.
        super().skip(example)
        self.print_yellow("S", end="")

    def finish(self, not_executed_examples: list[Example]) -> None:
        # pyre-fixme[16]: `DSLDebugMixin` has no attribute `finish`.
        super().finish(not_executed_examples)
        # pyre-fixme[16]: `ProgressFormatter` has no attribute `results`.
        # pyre-fixme[16]: `ProgressFormatter` has no attribute `dsl_debug`.
        if self.results["fail"] and not self.dsl_debug:
            self.print_red("\nFailures:")
            for number, result in enumerate(self.results["fail"]):
                result = cast(dict[str, Union[Example, BaseException]], result)
                print("")
                self.print_failed_example(
                    number + 1,
                    result["example"],  # type: ignore
                    result["exception"],  # type: ignore
                )
        print("")


class DocumentFormatter(
    VerboseFinishMixin, DSLDebugMixin, SlowImportWarningMixin, FailurePrinterMixin
):
    def get_dsl_debug_indent(self, example: Example) -> str:
        return "  " * (example.context.depth + 1)

    def new_context(self, context: Context) -> None:
        self.print_bright(
            "{}{}{}".format("  " * context.depth, "*" if context.focus else "", context)
        )

    def _color_output(self) -> bool:
        # pyre-fixme[16]: `DocumentFormatter` has no attribute `force_color`.
        return sys.stdout.isatty() or self.force_color

    def success(self, example: Example) -> None:
        # pyre-fixme[16]: `VerboseFinishMixin` has no attribute `success`.
        super().success(example)
        self.print_green(
            "{indent}{focus}{example}{pass_text}".format(
                indent="  " * (example.context.depth + 1),
                focus="*" if example.focus else "",
                example=example,
                pass_text="" if self._color_output() else ": PASS",
            )
        )

    def fail(self, example: Example, exception: BaseException) -> None:
        # pyre-fixme[16]: Module `lib` has no attribute `AggregatedExceptions`.
        if isinstance(exception, AggregatedExceptions) and 1 == len(
            # pyre-fixme[16]: `BaseException` has no attribute `exceptions`.
            exception.exceptions
        ):
            exception = exception.exceptions[0]

        # pyre-fixme[16]: `VerboseFinishMixin` has no attribute `fail`.
        super().fail(example, exception)

        self.print_red(
            "{indent}{focus}{example}: {ex_class}: {ex_message}".format(
                indent="  " * (example.context.depth + 1),
                focus="*" if example.focus else "",
                example=example,
                ex_class=type(exception).__name__,
                ex_message=str(exception).split("\n")[0],
            )
        )

    def skip(self, example: Example) -> None:
        # pyre-fixme[16]: `VerboseFinishMixin` has no attribute `skip`.
        super().skip(example)
        self.print_yellow(
            "{indent}{focus}{example}{skip_text}".format(
                indent="  " * (example.context.depth + 1),
                focus="*" if example.focus else "",
                example=example,
                skip_text="" if self._color_output() else ": SKIP",
            )
        )


class LongFormatter(
    VerboseFinishMixin, DSLDebugMixin, SlowImportWarningMixin, FailurePrinterMixin
):
    def get_dsl_debug_indent(self, example: Example) -> str:
        return "  "

    def new_example(self, example: Example) -> None:
        self.print_bright(
            "{}{}: ".format(
                "*" if example.context.focus else "", example.context.full_name
            ),
            end="",
        )
        # pyre-fixme[16]: `LongFormatter` has no attribute `dsl_debug`.
        if self.dsl_debug:
            print("")

    def _color_output(self) -> bool:
        # pyre-fixme[16]: `LongFormatter` has no attribute `force_color`.
        return sys.stdout.isatty() or self.force_color

    def success(self, example: Example) -> None:
        # pyre-fixme[16]: `VerboseFinishMixin` has no attribute `success`.
        super().success(example)
        # pyre-fixme[16]: `LongFormatter` has no attribute `dsl_debug`.
        if self.dsl_debug:
            print("  ", end="")
        self.print_green(
            "{focus}{example}{pass_text}".format(
                focus="*" if example.focus else "",
                example=example,
                pass_text="" if self._color_output() else ": PASS",
            )
        )

    def fail(self, example: Example, exception: BaseException) -> None:
        # pyre-fixme[16]: Module `lib` has no attribute `AggregatedExceptions`.
        if isinstance(exception, AggregatedExceptions) and 1 == len(
            # pyre-fixme[16]: `BaseException` has no attribute `exceptions`.
            exception.exceptions
        ):
            exception = exception.exceptions[0]

        # pyre-fixme[16]: `VerboseFinishMixin` has no attribute `fail`.
        super().fail(example, exception)
        # pyre-fixme[16]: `LongFormatter` has no attribute `dsl_debug`.
        if self.dsl_debug:
            print("  ", end="")
        self.print_red(
            "{focus}{example}: {ex_class}: {ex_message}".format(
                focus="*" if example.focus else "",
                example=example,
                ex_class=type(exception).__name__,
                ex_message=str(exception).split("\n")[0],
            ),
        )

    def skip(self, example: Example) -> None:
        # pyre-fixme[16]: `VerboseFinishMixin` has no attribute `skip`.
        super().skip(example)
        # pyre-fixme[16]: `LongFormatter` has no attribute `dsl_debug`.
        if self.dsl_debug:
            print("  ", end="")
        self.print_yellow(
            "{focus}{example}{skip_text}".format(
                focus="*" if example.focus else "",
                example=example,
                skip_text="" if self._color_output() else ": SKIP",
            )
        )


##
## Runner
##


class Runner:
    """
    Execute examples contained in given contexts.
    """

    def __init__(
        self,
        contexts: list[Context],
        formatter: SlowImportWarningMixin | DocumentFormatter,
        shuffle: bool = False,
        seed: int | None = None,
        focus: bool = False,
        fail_fast: bool = False,
        fail_if_focused: bool = False,
        names_text_filter: str | None = None,
        names_regex_filter: Pattern | None = None,
        names_regex_exclude: Pattern | None = None,
        quiet: bool = False,
        slow_callback_is_not_fatal: bool = False,
    ) -> None:
        self.contexts = contexts
        self.formatter = formatter
        self.shuffle = shuffle
        self.seed = seed
        self.focus = focus
        self.fail_fast = fail_fast
        self.fail_if_focused = fail_if_focused
        self.names_text_filter = names_text_filter
        self.names_regex_filter = names_regex_filter
        self.names_regex_exclude = names_regex_exclude
        self.quiet = quiet
        self.slow_callback_is_not_fatal = slow_callback_is_not_fatal

    def _run_example(self, example: Example) -> None:
        if example.focus and self.fail_if_focused:
            raise AssertionError(
                "Focused example not allowed with --fail-if-focused"
                ". Please remove the focus to allow the test to run."
            )
        if self.quiet:
            stdout = io.StringIO()
            stderr = io.StringIO()
            example_exception = None
            with redirect_stdout(stdout), redirect_stderr(stderr):
                try:
                    _ExampleRunner(
                        example, self.formatter, self.slow_callback_is_not_fatal
                    ).run()
                except BaseException as ex:
                    example_exception = ex
            if example_exception:
                # pyre-fixme[16]: Module `lib` has no attribute `Skip`.
                if not isinstance(example_exception, Skip):
                    if stdout.getvalue():
                        print(f"stdout:\n{stdout.getvalue()}")
                    if stderr.getvalue():
                        print(f"stderr:\n{stderr.getvalue()}")
                raise example_exception
        else:
            _ExampleRunner(
                example, self.formatter, self.slow_callback_is_not_fatal
            ).run()

    def run(self) -> int:
        """
        Execute all examples in all contexts.
        """
        sys.stdout.flush()
        sys.stderr.flush()
        executed_examples = []
        exit_code = 0
        for example in self._to_execute_examples:
            executed_examples.append(example)
            # pyre-fixme[16]: Item `DocumentFormatter` of `Union[DocumentFormatter,
            #  SlowImportWarningMixin]` has no attribute `start`.
            self.formatter.start(example)
            sys.stdout.flush()
            sys.stderr.flush()
            try:
                self._run_example(example)
            # pyre-fixme[66]: Exception handler type annotation `unknown` must
            #  extend BaseException.
            # pyre-fixme[16]: Module `lib` has no attribute `Skip`.
            except Skip:
                # pyre-fixme[16]: Item `SlowImportWarningMixin` of
                #  `Union[DocumentFormatter, SlowImportWarningMixin]` has no attribute
                #  `skip`.
                self.formatter.skip(example)
            except BaseException as exception:
                # pyre-fixme[16]: Item `SlowImportWarningMixin` of
                #  `Union[DocumentFormatter, SlowImportWarningMixin]` has no attribute
                #  `fail`.
                self.formatter.fail(example, exception)
                exit_code = 1
                if self.fail_fast:
                    break
            else:
                # pyre-fixme[16]: Item `SlowImportWarningMixin` of
                #  `Union[DocumentFormatter, SlowImportWarningMixin]` has no attribute
                #  `success`.
                self.formatter.success(example)
        not_executed_examples = [
            example
            for example in self._all_examples
            if example not in executed_examples
        ]
        # pyre-fixme[16]: Item `SlowImportWarningMixin` of `Union[DocumentFormatter,
        #  SlowImportWarningMixin]` has no attribute `finish`.
        self.formatter.finish(not_executed_examples)
        sys.stdout.flush()
        sys.stderr.flush()
        return exit_code

    def _filter(self, example: Example, focus: bool) -> bool:
        if focus and not example.focus:
            return False

        if self.names_regex_exclude:
            if self.names_regex_exclude.search(example.full_name):
                return False

        if self.names_text_filter:
            if self.names_text_filter not in example.full_name:
                return False

        if self.names_regex_filter:
            if not self.names_regex_filter.search(example.full_name):
                return False

        return True

    @property
    def _all_examples(self) -> list[Example]:
        examples = [
            example for context in self.contexts for example in context.all_examples
        ]
        if self.shuffle:
            if self.seed:
                random.seed(self.seed)
            random.shuffle(examples)
        return examples

    @property
    def _to_execute_examples(self) -> list[Example]:
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
