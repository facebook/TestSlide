# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import inspect
import io
import os
import os.path
import random
import re
import sys
import time
import traceback
from contextlib import redirect_stderr, redirect_stdout
from importlib import import_module
from typing import Any, Callable, Dict, List, Optional, Pattern, Union, cast

import psutil
import pygments
import pygments.formatters
import pygments.lexers

import testslide

from . import AggregatedExceptions, Context, Example, Skip, _ExampleRunner

##
## Base
##


class BaseFormatter:
    """
    Formatter base class. To be paired with Runner, to process / output example
    execution results.
    """

    def __init__(
        self,
        import_module_names: List[str],
        force_color: bool = False,
        import_secs: Optional[float] = None,
        trim_path_prefix: Optional[str] = None,
        show_testslide_stack_trace: bool = False,
        dsl_debug: bool = False,
    ) -> None:
        self.import_module_names = import_module_names
        self.force_color = force_color
        self.import_secs = import_secs
        self._import_secs_warn = True
        self.trim_path_prefix = trim_path_prefix
        self.show_testslide_stack_trace = show_testslide_stack_trace
        self.dsl_debug = dsl_debug
        self.current_hierarchy: List[Context] = []
        self.results: Dict[
            str, List[Union[Example, Dict[str, Union[Example, BaseException]]]]
        ] = {
            "success": [],
            "fail": [],
            "skip": [],
        }
        self.start_time = psutil.Process(os.getpid()).create_time()
        self.end_time: Optional[float] = None
        self.duration_secs: Optional[float] = None

    # Example Discovery

    def discovery_start(self) -> None:
        """
        To be called before example discovery starts.
        """
        pass

    def example_discovered(self, example: Example) -> None:
        """
        To be called when a new example is discovered.
        """
        print(example.full_name)

    def discovery_finish(self) -> None:
        """
        To be called before example discovery finishes.
        """
        pass

    # Test Execution

    def start(self, example: Example) -> None:
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

    def new_context(self, context: Context) -> None:
        """
        Called before an example execution, when its context is different from
        previous executed example.
        """
        pass

    def new_example(self, example: Example) -> None:
        """
        Called before an example execution.
        """
        pass

    def success(self, example: Example) -> None:
        """
        Called when an example was Successfuly executed.
        """
        self.results["success"].append(example)

    def fail(self, example: Example, exception: BaseException) -> None:
        """
        Called when an example failed on execution.
        """
        self.results["fail"].append({"example": example, "exception": exception})

    def skip(self, example: Example) -> None:
        """
        Called when an example had the execution skipped.
        """
        self.results["skip"].append(example)

    def finish(self, not_executed_examples: List[Example]) -> None:
        """
        Called when all examples finished execution.
        """
        self.end_time = time.time()
        self.duration_secs = self.end_time - self.start_time

    # DSL

    def dsl_example(self, example: Example, code: Callable) -> None:
        pass

    def dsl_before(self, example: Example, code: Callable) -> None:
        pass

    def dsl_after(self, example: Example, code: Callable) -> None:
        pass

    def dsl_around(self, example: Example, code: Callable) -> None:
        pass

    def dsl_memoize(self, example: Example, code: Callable) -> None:
        pass

    def dsl_memoize_before(self, example: Example, code: Callable) -> None:
        pass

    def dsl_function(self, example: Example, code: Callable) -> None:
        pass


##
## Mixins
##


class ColorFormatterMixin(BaseFormatter):
    @property
    def colored(self) -> bool:
        return sys.stdout.isatty() or self.force_color

    def remove_terminal_escape(self, text: str) -> str:
        return re.sub("\033\\[[0-9;]+m", "", text)

    def _format_attrs(self, attrs: str, *values: Any) -> str:
        text = "".join([str(value) for value in values])
        if self.colored:
            return "\033[0m\033[{attrs}m{text}\033[0m".format(attrs=attrs, text=text)
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
    TESTSLIDE_PATH: str = os.path.abspath(os.path.dirname(testslide.__file__))

    def _get_test_module_index(self, tb: traceback.StackSummary) -> Optional[int]:
        test_module_paths = [
            import_module(import_module_name).__file__
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
            if not self.show_testslide_stack_trace:
                if test_module_index is not None and index < test_module_index:
                    continue
                if os.path.abspath(path).startswith(self.TESTSLIDE_PATH):
                    continue
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
                    pygments.formatters.TerminalFormatter(),
                )
            row_text = "\n".join(
                "{indent}    {line}".format(indent=indent, line=line)
                for line in row_text.split("\n")[:-1]
            )
            print(row_text)

        if exception.__cause__:
            self._print_stack_trace(exception.__cause__, cause_depth=cause_depth + 1)

    def print_failed_example(
        self,
        number: int,
        example: Example,
        exception: BaseException,
    ) -> None:
        self.print_bright(
            "  {number}) {context}: {example}".format(
                number=number, context=example.context.full_name, example=example
            )
        )
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
        if self.import_secs and self.import_secs > 1 and self._import_secs_warn:
            self.print_yellow(
                "Warning: Importing test modules alone took %.1fs! To remove this slow "
                "down remove object construction from module level. If not possible, "
                "consider using/ lazy_import(). Try using --import-profiler to profile "
                "your imports." % (self.import_secs)
            )
            self._import_secs_warn = False


class DSLDebugMixin:
    def get_dsl_debug_indent(self, example: Example) -> str:
        return ""

    def _dsl_print(self, example: Example, description: str, code: Callable) -> None:
        lineno: Union[str, int]
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
        if file and file.startswith(os.path.dirname(__file__)):
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
            return "\033[0m\033[{attrs}m{text}\033[0m".format(attrs=attrs, text=text)
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

    def _get_ascii_logo_lines(self) -> List[str]:
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
""".split(
            "\n"
        )[
            1:8
        ]

    def _get_summary_lines(
        self, total: int, success: int, fail: int, skip: int, not_executed_examples: int
    ) -> List[str]:
        summary_lines: List[str] = []

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

    def finish(self, not_executed_examples: List[Example]) -> None:
        super().finish(not_executed_examples)
        success = len(self.results["success"])
        fail = len(self.results["fail"])
        skip = len(self.results["skip"])
        total = success + fail + skip
        if self.results["fail"]:
            self.print_red("\nFailures:")
            for number, result in enumerate(self.results["fail"]):
                result = cast(Dict[str, Union[Example, BaseException]], result)
                print("")
                self.print_failed_example(  # type: ignore
                    number + 1, result["example"], result["exception"]  # type: ignore
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
        super().new_example(example)
        if self.dsl_debug:
            print("")

    def success(self, example: Example) -> None:
        super().success(example)
        self.print_green(".", end="")

    def fail(self, example: Example, exception: BaseException) -> None:
        super().fail(example, exception)
        self.print_red("F", end="")

    def skip(self, example: Example) -> None:
        super().skip(example)
        self.print_yellow("S", end="")

    def finish(self, not_executed_examples: List[Example]) -> None:
        super().finish(not_executed_examples)
        if self.results["fail"] and not self.dsl_debug:
            self.print_red("\nFailures:")
            for number, result in enumerate(self.results["fail"]):
                result = cast(Dict[str, Union[Example, BaseException]], result)
                print("")
                self.print_failed_example(
                    number + 1, result["example"], result["exception"]  # type: ignore
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
        return sys.stdout.isatty() or self.force_color

    def success(self, example: Example) -> None:
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
        if isinstance(exception, AggregatedExceptions) and 1 == len(
            exception.exceptions
        ):
            exception = exception.exceptions[0]

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
        if self.dsl_debug:
            print("")

    def _color_output(self) -> bool:
        return sys.stdout.isatty() or self.force_color

    def success(self, example: Example) -> None:
        super().success(example)
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
        if isinstance(exception, AggregatedExceptions) and 1 == len(
            exception.exceptions
        ):
            exception = exception.exceptions[0]

        super().fail(example, exception)
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
        super().skip(example)
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
        contexts: List[Context],
        formatter: Union[SlowImportWarningMixin, DocumentFormatter],
        shuffle: bool = False,
        seed: int = None,
        focus: bool = False,
        fail_fast: bool = False,
        fail_if_focused: bool = False,
        names_text_filter: Optional[str] = None,
        names_regex_filter: Optional[Pattern] = None,
        names_regex_exclude: Optional[Pattern] = None,
        quiet: bool = False,
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
                    _ExampleRunner(example, self.formatter).run()
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
            _ExampleRunner(example, self.formatter).run()

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
    def _all_examples(self) -> List[Example]:
        examples = [
            example for context in self.contexts for example in context.all_examples
        ]
        if self.shuffle:
            if self.seed:
                random.seed(self.seed)
            random.shuffle(examples)
        return examples

    @property
    def _to_execute_examples(self) -> List[Example]:
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
