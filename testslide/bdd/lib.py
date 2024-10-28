# pyre-unsafe
import asyncio
import asyncio.log
import inspect
import os
import re
import sys
import time
import types
import unittest
from contextlib import contextmanager
from functools import partial
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple, Type, Union

import psutil

import testslide.core.matchers
import testslide.core.mock_callable
import testslide.core.mock_constructor
import testslide.core.patch_attribute
from testslide.core import TestCase
from testslide.core.strict_mock import StrictMock  # noqa

asyncio_run = partial(asyncio.run, debug=True)


if sys.version_info < (3, 8):
    get_all_tasks = asyncio.Task.all_tasks
else:
    get_all_tasks = asyncio.all_tasks


class LeftOverActiveTasks(BaseException):
    """Risen when unfinished asynchronous tasks are detected."""

    pass


class Skip(Exception):
    """
    Raised by an example when it is skipped
    """

    pass


class UnexpectedSuccess(Exception):
    """
    Raised by an example when it unexpectedly succeeded
    """


class SlowCallback(Exception):
    """
    Raised by TestSlide when an asyncio slow callback warning is detected
    """


def get_active_tasks():
    return [
        task for task in get_all_tasks() if not task.done() and not task.cancelled()
    ]


async def _async_ensure_no_leaked_tasks(coro):
    before_example_tasks = get_active_tasks()
    result = await coro
    after_example_tasks = get_active_tasks()
    new_still_running_tasks = set(after_example_tasks) - set(before_example_tasks)
    if new_still_running_tasks:
        tasks_str = "\n".join(str(task) for task in new_still_running_tasks)
        raise LeftOverActiveTasks(
            "Some tasks were started but did not finish yet, are you missing "
            f"an `await` somewhere?\nRunning tasks:\n {tasks_str}"
        )

    return result


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
            str, List[Union["Example", Dict[str, Union["Example", BaseException]]]]
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

    def example_discovered(self, example: "Example") -> None:
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

    def start(self, example: "Example") -> None:
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

    def new_context(self, context: "Context") -> None:
        """
        Called before an example execution, when its context is different from
        previous executed example.
        """
        pass

    def new_example(self, example: "Example") -> None:
        """
        Called before an example execution.
        """
        pass

    def success(self, example: "Example") -> None:
        """
        Called when an example was Successfuly executed.
        """
        self.results["success"].append(example)

    def fail(self, example: "Example", exception: BaseException) -> None:
        """
        Called when an example failed on execution.
        """
        self.results["fail"].append({"example": example, "exception": exception})

    def skip(self, example: "Example") -> None:
        """
        Called when an example had the execution skipped.
        """
        self.results["skip"].append(example)

    def finish(self, not_executed_examples: List["Example"]) -> None:
        """
        Called when all examples finished execution.
        """
        self.end_time = time.time()
        self.duration_secs = self.end_time - self.start_time

    # DSL

    def dsl_example(self, example: "Example", code: Callable) -> None:
        pass

    def dsl_before(self, example: "Example", code: Callable) -> None:
        pass

    def dsl_after(self, example: "Example", code: Callable) -> None:
        pass

    def dsl_around(self, example: "Example", code: Callable) -> None:
        pass

    def dsl_memoize(self, example: "Example", code: Callable) -> None:
        pass

    def dsl_memoize_before(self, example: "Example", code: Callable) -> None:
        pass

    def dsl_function(self, example: "Example", code: Callable) -> None:
        pass


class _ContextData:
    """
    To be used as a repository of context specific data, used during each
    example execution.
    """

    def _init_sub_example(self) -> None:
        self._sub_examples_agg_ex = AggregatedExceptions()

        def real_assert_sub_examples(self: "_ContextData") -> None:
            if self._sub_examples_agg_ex.exceptions:
                self._sub_examples_agg_ex.raise_correct_exception()

        if self._example.is_async:

            async def assert_sub_examples(self: "_ContextData") -> None:
                real_assert_sub_examples(self)

        else:

            def assert_sub_examples(self: "_ContextData") -> None:  # type: ignore
                real_assert_sub_examples(self)

        self.after(assert_sub_examples)

    def _init_mocks(self) -> None:
        self.mock_callable = testslide.core.mock_callable.mock_callable
        self.mock_async_callable = testslide.core.mock_callable.mock_async_callable
        self.mock_constructor = testslide.core.mock_constructor.mock_constructor
        self.patch_attribute = testslide.core.patch_attribute.patch_attribute
        self._mock_callable_after_functions: List[Callable] = []

        def register_assertion(assertion: Callable) -> None:
            if self._example.is_async:

                async def f(_: _ContextData) -> None:
                    assertion()

            else:
                f = lambda _: assertion()
            self._mock_callable_after_functions.append(f)

        testslide.core.mock_callable.register_assertion = register_assertion

    def __init__(self, example: "Example", formatter: "BaseFormatter") -> None:
        self._example = example
        self._formatter = formatter
        self._context = example.context
        self._after_functions: List[Callable] = []
        self._test_case = unittest.TestCase()
        self._init_sub_example()
        self._init_mocks()

    @staticmethod
    def _not_callable(self: "_ContextData") -> None:
        raise BaseException("This function should not be called outside test code.")

    @property
    def _all_methods(self) -> Dict[str, Callable]:
        return self._context.all_context_data_methods

    @property
    def _all_memoizable_attributes(self) -> Dict[str, Callable]:
        return self._context.all_context_data_memoizable_attributes

    def __setattr__(self, name: str, value: Any) -> None:
        if self.__dict__.get(name) and self.__dict__[name] != value:
            raise AttributeError(
                f"Attribute {repr(name)} can not be reset.\n"
                "Resetting attribute values is not permitted as it can create "
                "confusion and taint test signal.\n"
                "You can use memoize/memoize_before instead, as they allow "
                "attributes from parent contexs to be overridden consistently "
                "by sub-contexts.\n"
                "Details and examples at the documentation: "
                "https://testslide.readthedocs.io/en/main/testslide_dsl/context_attributes_and_functions/index.html"
            )
        else:
            super(_ContextData, self).__setattr__(name, value)

    def __getattr__(self, name: str) -> Any:
        if name in self._all_methods.keys():

            def static(*args: Any, **kwargs: Any) -> Any:
                return self._all_methods[name](self, *args, **kwargs)

            self.__dict__[name] = static

        if name in self._all_memoizable_attributes.keys():
            attribute_code = self._all_memoizable_attributes[name]
            if self._example.is_async and inspect.iscoroutinefunction(attribute_code):
                raise ValueError(
                    f"Function can not be a coroutine function: {repr(attribute_code)}"
                )
            self._formatter.dsl_memoize(self._example, attribute_code)
            self.__dict__[name] = attribute_code(self)

        try:
            return self.__dict__[name]
        except KeyError:
            # Forward assert* methods to unittest.TestCase
            if re.match("^assert", name) and hasattr(self._test_case, name):
                return getattr(self._test_case, name)
            raise AttributeError(
                "Context '{}' has no attribute '{}'".format(self._context, name)
            )

    def after(self, after_code: Callable) -> Callable:
        """
        Use this to decorate a function to be registered to be executed after
        the example code.
        """
        self._after_functions.append(after_code)
        return self._not_callable

    @contextmanager
    def sub_example(self, name: Optional[str] = None) -> Iterator[None]:
        """
        Use this as a context manager many times inside the same
        example. Failures in the code inside the context manager
        will be aggregated, and reported individually at the end.
        """
        with self._sub_examples_agg_ex.catch():
            yield

    def async_run_with_health_checks(self, coro):
        """
        Runs the given coroutine in a new event loop, and ensuring there's no
        task leakage.
        """
        result = asyncio_run(_async_ensure_no_leaked_tasks(coro))

        return result


class AggregatedExceptions(Exception):
    """
    Aggregate example execution exceptions.
    """

    def __init__(self) -> None:
        super(AggregatedExceptions, self).__init__()
        self.exceptions: List[BaseException] = []

    def append_exception(self, exception: BaseException) -> None:
        if isinstance(exception, AggregatedExceptions):
            self.exceptions.extend(exception.exceptions)
        else:
            self.exceptions.append(exception)

    @contextmanager
    def catch(self) -> Iterator[None]:
        try:
            yield
        except BaseException as exception:
            self.append_exception(exception)

    def __str__(self) -> str:
        return "{} failures.\n".format(len(self.exceptions)) + "\n".join(
            f"{type(e)}: {str(e)}" for e in self.exceptions
        )

    def raise_correct_exception(self) -> None:
        if not self.exceptions:
            return
        ex_types = {type(ex) for ex in self.exceptions}
        if Skip in ex_types or unittest.SkipTest in ex_types:
            raise Skip()
        elif len(self.exceptions) == 1:
            raise self.exceptions[0]
        else:
            raise self
            if len(self.exceptions) == 1:
                raise self.exceptions[0]
            else:
                raise self


class _TestSlideTestResult(unittest.TestResult):
    """
    Concrete unittest.TestResult to allow unttest.TestCase integration, by
    aggregating failures at an AggregatedExceptions instance.
    """

    def __init__(self) -> None:
        super(_TestSlideTestResult, self).__init__()
        self.aggregated_exceptions = AggregatedExceptions()

    def _add_exception(
        self,
        err: Tuple[
            Type[BaseException],
            BaseException,
            Optional[types.TracebackType],
        ],
    ) -> None:
        exc_type, exc_value, exc_traceback = err
        self.aggregated_exceptions.append_exception(exc_value)

    # pyre-fixme[14]: `addError` overrides method defined in `TestResult`
    #  inconsistently.
    def addError(  # type:ignore
        self,
        test: "TestCase",
        err: Tuple[
            Type[BaseException],
            BaseException,
            types.TracebackType,
        ],
    ) -> None:
        """Called when an error has occurred. 'err' is a tuple of values as
        returned by sys.exc_info().
        """
        super(_TestSlideTestResult, self).addError(test, err)  # type: ignore
        self._add_exception(err)

    # pyre-fixme[14]: `addFailure` overrides method defined in `TestResult`
    #  inconsistently.
    def addFailure(  # type:ignore
        self,
        test: "TestCase",
        err: Tuple[
            Type[BaseException],
            BaseException,
            types.TracebackType,
        ],
    ) -> None:
        """Called when an error has occurred. 'err' is a tuple of values as
        returned by sys.exc_info()."""
        super(_TestSlideTestResult, self).addFailure(test, err)
        self._add_exception(err)

    def addSkip(self, test: "TestCase", reason: str) -> None:  # type: ignore
        """Called when the test case test is skipped. reason is the reason
        the test gave for skipping."""
        super(_TestSlideTestResult, self).addSkip(test, reason)
        self._add_exception((type(Skip), Skip(), None))  # type: ignore

    def addUnexpectedSuccess(self, test: "TestCase") -> None:  # type: ignore
        """Called when the test case test was marked with the expectedFailure()
        decorator, but succeeded."""
        super(_TestSlideTestResult, self).addUnexpectedSuccess(test)
        self._add_exception((type(UnexpectedSuccess), UnexpectedSuccess(), None))  # type: ignore

    def addSubTest(self, test: "TestCase", subtest: "TestCase", err: Tuple[Optional[Type[BaseException]], Optional[BaseException], Optional[types.TracebackType]]) -> None:  # type: ignore
        """Called at the end of a subtest.
        'err' is None if the subtest ended successfully, otherwise it's a
        tuple of values as returned by sys.exc_info().
        """
        super(_TestSlideTestResult, self).addSubTest(test, subtest, err)  # type: ignore
        if err:
            self._add_exception(err)  # type: ignore


class Example:
    """
    Individual example.
    """

    def __init__(
        self,
        name: str,
        code: Callable,
        context: "Context",
        skip: bool = False,
        focus: bool = False,
    ) -> None:
        self.name = name
        self.code = code
        self.is_async = inspect.iscoroutinefunction(self.code)
        self.context = context
        self.__dict__["skip"] = skip
        self.__dict__["focus"] = focus

    @property
    def full_name(self) -> str:
        return "{context_full_name}: {example_name}".format(
            context_full_name=self.context.full_name, example_name=self.name
        )

    @property
    def skip(self) -> bool:
        """
        True if the example of its context is marked to be skipped.
        """
        return any([self.context.skip, self.__dict__["skip"]])

    @property
    def focus(self) -> bool:
        """
        True if the example of its context is marked to be focused.
        """
        return any([self.context.focus, self.__dict__["focus"]])

    def __str__(self) -> str:
        return self.name


class Context:
    """
    Container for example contexts.
    """

    _SAME_CONTEXT_NAME_ERROR = "A context with the same name is already defined"

    # List of all top level contexts created
    all_top_level_contexts: List["Context"] = []

    # Constructor

    def __init__(
        self,
        name: str,
        parent_context: Optional["Context"] = None,
        shared: bool = False,
        skip: bool = False,
        focus: bool = False,
    ) -> None:
        """
        Creates a new context.
        """
        # Validate context name
        if parent_context:
            current_level_contexts = parent_context.children_contexts
        else:
            current_level_contexts = self.all_top_level_contexts
        if name in [context.name for context in current_level_contexts]:
            raise RuntimeError(self._SAME_CONTEXT_NAME_ERROR)

        self.name: str = name
        self.parent_context = parent_context
        self.shared = shared
        self.__dict__["skip"] = skip
        self.__dict__["focus"] = focus
        self.children_contexts: List["Context"] = []
        self.examples: List["Example"] = []
        self.before_functions: List[Callable] = []
        self.after_functions: List[Callable] = []
        self.around_functions: List[Callable] = []
        self.context_data_methods: Dict[str, Callable] = {}
        self.context_data_memoizable_attributes: Dict[str, Callable] = {}
        self.shared_contexts: Dict[str, "Context"] = {}

        if not self.parent_context and not self.shared:
            self.all_top_level_contexts.append(self)

    # Properties

    @property
    def parent_contexts(self) -> List["Context"]:
        """
        Returns a list of all parent contexts, from bottom to top.
        """
        final_list = []
        parent = self.parent_context
        while parent:
            final_list.append(parent)
            parent = parent.parent_context
        return final_list

    @property
    def depth(self) -> int:
        """
        Number of parent contexts this context has.
        """
        return len(self.parent_contexts)

    def _all_parents_as_dict(original: type) -> Callable[["Context"], Dict[str, Any]]:  # type: ignore # noqa: B902
        """
        Use as a decorator for empty functions named all_attribute_name, to make
        them return a dict with self.parent_context.all_attribute_name and
        self.attribute_name.
        """

        def get_all(self: "Context") -> Dict[str, Any]:
            final_dict: Dict[str, Any] = {}
            if self.parent_context:
                final_dict.update(getattr(self.parent_context, original.__name__))
            final_dict.update(getattr(self, original.__name__.split("all_")[1]))
            return final_dict

        return get_all

    def _all_parents_as_list(original: type) -> Callable[["Context"], List[Any]]:  # type: ignore  # noqa: B902
        """
        Use as a decorator for empty functions named all_attribute_name, to make
        them return a list with self.parent_context.all_attribute_name and
        self.attribute_name.
        """

        def get_all(self: "Context") -> List[Any]:
            final_list: List[str] = []
            if self.parent_context:
                final_list.extend(getattr(self.parent_context, original.__name__))
            final_list.extend(getattr(self, original.__name__.split("all_")[1]))
            return final_list

        return get_all

    @property  # type: ignore
    @_all_parents_as_dict
    def all_context_data_methods(self) -> None:
        """
        Returns a combined dict of all context_data_methods, including from
        parent contexts.
        """
        pass

    @property  # type: ignore
    @_all_parents_as_dict
    def all_context_data_memoizable_attributes(self) -> None:
        """
        Returns a combined dict of all context_data_memoizable_attributes,
        including from parent contexts.
        """
        pass

    @property  # type: ignore
    @_all_parents_as_list
    def all_around_functions(self) -> None:
        """
        Return a list of all around_functions, including from parent contexts.
        """
        pass

    @property  # type: ignore
    @_all_parents_as_list
    def all_before_functions(self) -> None:
        """
        Return a list of all before_functions, including from parent contexts.
        """
        pass

    @property  # type: ignore
    @_all_parents_as_list
    def all_after_functions(self) -> None:
        """
        Return a list of all after_functions, including from parent contexts.
        """
        pass

    @property  # type: ignore
    @_all_parents_as_dict
    def all_shared_contexts(self) -> None:
        """
        Returns a combined dict of all shared_contexts, including from parent
        contexts.
        """
        pass

    @property
    def all_examples(self) -> List[Example]:
        """
        List of of all examples in this context and nested contexts.
        """
        final_list = []
        final_list.extend(self.examples)
        for child_context in self.children_contexts:
            final_list.extend(child_context.all_examples)
        return final_list

    @property
    def hierarchy(self) -> List["Context"]:
        """
        Returns a list of all contexts in this hierarchy.
        """
        return [context for context in list(reversed(self.parent_contexts)) + [self]]

    @property
    def full_name(self) -> str:
        """
        Full context name, including parent contexts.
        """
        return ", ".join(str(context) for context in self.hierarchy)

    @property
    def skip(self) -> bool:
        """
        True if this context of any parent context are tagged to be skipped.
        """
        return any(context.__dict__["skip"] for context in self.hierarchy)

    @property
    def focus(self) -> bool:
        """
        True if this context of any parent context are tagged to be focused.
        """
        return any(context.__dict__["focus"] for context in self.hierarchy)

    def __str__(self) -> str:
        return self.name

    def add_child_context(
        self, name: str, skip: bool = False, focus: bool = False
    ) -> "Context":
        """
        Creates a nested context below self.
        """
        if name in [context.name for context in self.children_contexts]:
            raise RuntimeError(self._SAME_CONTEXT_NAME_ERROR)

        child_context = Context(name, parent_context=self, skip=skip, focus=focus)
        self.children_contexts.append(child_context)
        return child_context

    def add_example(
        self, name: str, example_code: Callable, skip: bool = False, focus: bool = False
    ) -> Example:
        """
        Add an example to this context.
        """
        if name in [example.name for example in self.examples]:
            raise RuntimeError(
                f"An example with the same name '{name}' is already defined"
            )

        self.examples.append(
            Example(name, code=example_code, context=self, skip=skip, focus=focus)
        )

        return self.examples[-1]

    def has_attribute(self, name: str) -> bool:
        return any(
            [
                name in self.context_data_methods.keys(),
                name in self.context_data_memoizable_attributes.keys(),
            ]
        )

    def add_function(self, name: str, function_code: Callable) -> None:
        """
        Add given function to example execution scope.
        """
        if self.has_attribute(name):
            raise AttributeError(
                'Attribute "{}" already set for context "{}"'.format(name, self)
            )
        self.context_data_methods[name] = function_code

    def add_memoized_attribute(
        self, name: str, memoizable_code: Callable, before: bool = False
    ) -> None:
        """
        Add given attribute name to execution scope, by lazily memoizing the return
        value of memoizable_code().
        """
        if self.has_attribute(name):
            raise AttributeError(
                'Attribute "{}" already set for context "{}"'.format(name, self)
            )
        self.context_data_memoizable_attributes[name] = memoizable_code

        if before:
            if inspect.iscoroutinefunction(memoizable_code):

                async def async_materialize_attribute(
                    context_data: _ContextData,
                ) -> None:
                    code = context_data._context.all_context_data_memoizable_attributes[
                        name
                    ]
                    context_data.__dict__[name] = await code(context_data)

                async_materialize_attribute._memoize_before_code = memoizable_code  # type: ignore
                self.before_functions.append(async_materialize_attribute)
            else:

                def materialize_attribute(context_data: _ContextData) -> None:
                    code = context_data._context.all_context_data_memoizable_attributes[
                        name
                    ]
                    context_data.__dict__[name] = code(context_data)

                materialize_attribute._memoize_before_code = memoizable_code  # type: ignore
                self.before_functions.append(materialize_attribute)

    def add_shared_context(self, name: str, shared_context_code: "Context") -> None:
        """
        Create a shared context.
        """
        if name in self.shared_contexts:
            raise RuntimeError("A shared context with the same name is already defined")
        self.shared_contexts[name] = shared_context_code

    def add_test_case(self, test_case: Type["TestCase"], attr_name: str) -> None:
        """
        Add around hooks to context from given unittest.TestCase class. Only
        hooks such as setUp or tearDown will be called, no tests will be
        included.
        """

        def wrap_test_case(self: "Context", example: Callable) -> None:
            def test_test_slide(_: Any) -> None:
                example()

            def exec_body(ns: Dict[str, Callable]) -> None:
                ns.update({"test_test_slide": test_test_slide})

            # Build a child class of given TestCase, with a defined test that
            # will run TestSlide example.
            test_slide_test_case = types.new_class(
                "TestSlideTestCase", bases=(test_case,), exec_body=exec_body
            )

            # This suite will only contain TestSlide's example test.
            test_suite = unittest.TestLoader().loadTestsFromName(
                "test_test_slide", test_slide_test_case  # type: ignore
            )
            setattr(self, attr_name, list(test_suite)[0])
            result = _TestSlideTestResult()
            test_suite(result=result)  # type: ignore
            if not result.wasSuccessful():
                result.aggregated_exceptions.raise_correct_exception()

        self.around_functions.append(wrap_test_case)


def reset() -> None:
    """
    Clear all defined contexts and hooks.
    """
    Context.all_top_level_contexts.clear()
