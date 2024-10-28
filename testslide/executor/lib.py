# pyre-unsafe
import asyncio
import asyncio.log
import contextlib
import inspect
import re
import sys
import warnings
from typing import Any, Callable, Dict, Iterator, List, Optional, TextIO, Type, Union

import testslide.core.matchers
import testslide.core.mock_callable
import testslide.core.mock_constructor
import testslide.core.patch_attribute

# pyre-fixme[21]: Could not find name `AggregatedExceptions` in `testslide.bdd.lib`
#  (stubbed).
# pyre-fixme[21]: Could not find name `BaseFormatter` in `testslide.bdd.lib` (stubbed).
# pyre-fixme[21]: Could not find name `Example` in `testslide.bdd.lib` (stubbed).
# pyre-fixme[21]: Could not find name `Skip` in `testslide.bdd.lib` (stubbed).
# pyre-fixme[21]: Could not find name `SlowCallback` in `testslide.bdd.lib` (stubbed).
# pyre-fixme[21]: Could not find name `_async_ensure_no_leaked_tasks` in
#  `testslide.bdd.lib` (stubbed).
# pyre-fixme[21]: Could not find name `asyncio_run` in `testslide.bdd.lib` (stubbed).
from testslide.bdd.lib import (
    _async_ensure_no_leaked_tasks,
    _ContextData,
    AggregatedExceptions,
    asyncio_run,
    BaseFormatter,
    Example,
    Skip,
    SlowCallback,
)
from testslide.core.strict_mock import StrictMock  # noqa


class _ExampleRunner:
    def __init__(
        self,
        # pyre-fixme[11]: Annotation `Example` is not defined as a type.
        example: Example,
        # pyre-fixme[11]: Annotation `BaseFormatter` is not defined as a type.
        formatter: BaseFormatter,
        slow_callback_is_not_fatal: bool = False,
    ) -> None:
        self.example = example
        self.formatter = formatter
        self.trim_path_prefix = self.formatter.trim_path_prefix
        self.slow_callback_is_not_fatal = slow_callback_is_not_fatal

    @staticmethod
    async def _fail_if_not_coroutine_function(
        func: Callable, *args: Any, **kwargs: Any
    ) -> None:
        if not inspect.iscoroutinefunction(func):
            raise ValueError(f"Function must be a coroutine function: {repr(func)}")
        return await func(*args, **kwargs)

    async def _real_async_run_all_hooks_and_example(
        self,
        context_data: _ContextData,
        around_functions: Optional[List[Callable]] = None,
    ) -> None:
        """
        ***********************************************************************
        ***********************************************************************
                                    WARNING
        ***********************************************************************
        ***********************************************************************

        This function **MUST** be keep the exact same execution flow of
        _sync_run_all_hooks_and_example()!!!
        """
        if around_functions is None:
            around_functions = list(reversed(self.example.context.all_around_functions))

        if not around_functions:
            # pyre-fixme[16]: Module `lib` has no attribute `AggregatedExceptions`.
            aggregated_exceptions = AggregatedExceptions()
            with aggregated_exceptions.catch():
                for before_code in self.example.context.all_before_functions:
                    if hasattr(before_code, "_memoize_before_code"):
                        self.formatter.dsl_memoize_before(
                            self.example, before_code._memoize_before_code
                        )
                    else:
                        self.formatter.dsl_before(self.example, before_code)
                    await self._fail_if_not_coroutine_function(
                        before_code, context_data
                    )
                self.formatter.dsl_example(self.example, self.example.code)
                # pyre-fixme[16]: Module `lib` has no attribute
                #  `_async_ensure_no_leaked_tasks`.
                await _async_ensure_no_leaked_tasks(
                    self._fail_if_not_coroutine_function(
                        self.example.code, context_data
                    )
                )
            after_functions: List[Callable] = []
            after_functions.extend(context_data._mock_callable_after_functions)
            after_functions.extend(self.example.context.all_after_functions)
            after_functions.extend(context_data._after_functions)

            for after_code in reversed(after_functions):
                with aggregated_exceptions.catch():
                    self.formatter.dsl_after(self.example, after_code)
                    await self._fail_if_not_coroutine_function(after_code, context_data)
            aggregated_exceptions.raise_correct_exception()
            return

        around_code = around_functions.pop()
        wrapped_called: List[bool] = []

        async def async_wrapped() -> None:
            wrapped_called.append(True)
            await self._real_async_run_all_hooks_and_example(
                context_data, around_functions
            )

        self.formatter.dsl_around(self.example, around_code)
        await self._fail_if_not_coroutine_function(
            around_code, context_data, async_wrapped
        )

        if not wrapped_called:
            raise RuntimeError(
                "Around hook "
                + repr(around_code.__name__)
                + " did not execute example code!"
            )

    @contextlib.contextmanager
    def _raise_if_asyncio_warnings(
        self, context_data: _ContextData, slow_callback_is_not_fatal: bool = False
    ) -> Iterator[None]:
        original_showwarning = warnings.showwarning
        caught_failures: List[Union[Exception, str]] = []

        def showwarning(
            message: str,
            category: Type[Warning],
            filename: str,
            lineno: int,
            file: Optional[TextIO] = None,
            line: Optional[str] = None,
        ) -> None:
            failure_warning_messages: Dict[Any, str] = {
                RuntimeWarning: "^coroutine '.+' was never awaited"
            }
            warning_class = type(message)
            pattern = failure_warning_messages.get(warning_class, None)
            if pattern and re.compile(pattern).match(str(message)):
                caught_failures.append(message)
            else:
                original_showwarning(message, category, filename, lineno, file, line)

        warnings.showwarning = showwarning  # type: ignore

        original_logger_warning = asyncio.log.logger.warning

        def logger_warning(msg: str, *args: Any, **kwargs: Any) -> None:
            if re.compile("^Executing .+ took .+ seconds$").match(str(msg)):
                msg = (
                    f"{msg}\n"
                    "During the execution of the async test a slow callback "
                    "that blocked the event loop was detected.\n"
                    "Tip: you can customize the detection threshold with:\n"
                    "  asyncio.get_running_loop().slow_callback_duration = seconds"
                )
                # pyre-fixme[16]: Module `lib` has no attribute `SlowCallback`.
                caught_failures.append(SlowCallback(msg % args))
            else:
                original_logger_warning(msg, *args, **kwargs)

        if not slow_callback_is_not_fatal:
            asyncio.log.logger.warning = logger_warning  # type: ignore

        # pyre-fixme[16]: Module `lib` has no attribute `AggregatedExceptions`.
        aggregated_exceptions = AggregatedExceptions()

        try:
            with aggregated_exceptions.catch():
                yield
        finally:
            warnings.showwarning = original_showwarning
            asyncio.log.logger.warning = original_logger_warning  # type: ignore
            for failure in caught_failures:
                with aggregated_exceptions.catch():
                    raise failure  # type: ignore
            aggregated_exceptions.raise_correct_exception()

    def _async_run_all_hooks_and_example(self, context_data: _ContextData) -> None:
        coro = self._real_async_run_all_hooks_and_example(context_data)
        with self._raise_if_asyncio_warnings(
            context_data, self.slow_callback_is_not_fatal
        ):
            # pyre-fixme[16]: Module `lib` has no attribute `asyncio_run`.
            asyncio_run(coro)

    @staticmethod
    def _fail_if_coroutine_function(
        func: Callable, *args: Any, **kwargs: Any
    ) -> Optional[Any]:
        if inspect.iscoroutinefunction(func):
            raise ValueError(f"Function can not be a coroutine function: {repr(func)}")
        return func(*args, **kwargs)

    def _sync_run_all_hooks_and_example(
        self,
        context_data: _ContextData,
        around_functions: Optional[List[Callable]] = None,
    ) -> None:
        """
        ***********************************************************************
        ***********************************************************************
                                    WARNING
        ***********************************************************************
        ***********************************************************************

        This function **MUST** be keep the exact same execution flow of
        _real_async_run_all_hooks_and_example()!!!
        """
        if around_functions is None:
            around_functions = list(reversed(self.example.context.all_around_functions))

        if not around_functions:
            # pyre-fixme[16]: Module `lib` has no attribute `AggregatedExceptions`.
            aggregated_exceptions = AggregatedExceptions()
            with aggregated_exceptions.catch():
                for before_code in self.example.context.all_before_functions:
                    if hasattr(before_code, "_memoize_before_code"):
                        self.formatter.dsl_memoize_before(
                            self.example, before_code._memoize_before_code
                        )
                    else:
                        self.formatter.dsl_before(self.example, before_code)
                    self._fail_if_coroutine_function(before_code, context_data)
                self.formatter.dsl_example(self.example, self.example.code)
                self._fail_if_coroutine_function(self.example.code, context_data)
            after_functions: List[Callable] = []
            after_functions.extend(context_data._mock_callable_after_functions)
            after_functions.extend(self.example.context.all_after_functions)
            after_functions.extend(context_data._after_functions)
            for after_code in reversed(after_functions):
                with aggregated_exceptions.catch():
                    self.formatter.dsl_after(self.example, after_code)
                    self._fail_if_coroutine_function(after_code, context_data)
            aggregated_exceptions.raise_correct_exception()
            return
        around_code = around_functions.pop()

        wrapped_called: List[bool] = []

        def wrapped() -> None:
            wrapped_called.append(True)
            self._sync_run_all_hooks_and_example(context_data, around_functions)

        self.formatter.dsl_around(self.example, around_code)
        self._fail_if_coroutine_function(around_code, context_data, wrapped)

        if not wrapped_called:
            raise RuntimeError(
                "Around hook "
                + repr(around_code.__name__)
                + " did not execute example code!"
            )

    def run(self) -> None:
        try:
            if self.example.skip:
                # pyre-fixme[16]: Module `lib` has no attribute `Skip`.
                raise Skip()
            context_data = _ContextData(self.example, self.formatter)
            if self.example.is_async:
                self._async_run_all_hooks_and_example(context_data)
            else:
                self._sync_run_all_hooks_and_example(context_data)
        finally:
            sys.stdout.flush()
            sys.stderr.flush()
            testslide.core.mock_callable.unpatch_all_callable_mocks()
            testslide.core.mock_constructor.unpatch_all_constructor_mocks()
            testslide.core.patch_attribute.unpatch_all_mocked_attributes()
