# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from contextlib import contextmanager

import sys
import asyncio.log
import unittest
import contextlib
import re
import types
import asyncio
import inspect
import warnings

import testslide.mock_callable
import testslide.mock_constructor
import testslide.matchers
import testslide.patch_attribute
from testslide.strict_mock import StrictMock  # noqa


if sys.version_info < (3, 6):
    raise RuntimeError("Python >=3.6 required.")


def _importer(target):
    components = target.split(".")
    import_path = components.pop(0)
    thing = __import__(import_path)

    def dot_lookup(thing, comp, import_path):
        try:
            return getattr(thing, comp)
        except AttributeError:
            __import__(import_path)
            return getattr(thing, comp)

    for comp in components:
        import_path += ".%s" % comp
        thing = dot_lookup(thing, comp, import_path)
    return thing


class _ContextData(object):
    """
    To be used as a repository of context specific data, used during each
    example execution.
    """

    def _init_sub_example(self):
        self._sub_examples_agg_ex = AggregatedExceptions()

        def real_assert_sub_examples(self):
            if self._sub_examples_agg_ex.exceptions:
                self._sub_examples_agg_ex.raise_correct_exception()

        if self._example.is_async:

            async def assert_sub_examples(self):
                real_assert_sub_examples(self)

        else:

            def assert_sub_examples(self):
                real_assert_sub_examples(self)

        self.after(assert_sub_examples)

    def _init_mocks(self):
        self.mock_callable = testslide.mock_callable.mock_callable
        self.mock_async_callable = testslide.mock_callable.mock_async_callable
        self.mock_constructor = testslide.mock_constructor.mock_constructor
        self.patch_attribute = testslide.patch_attribute.patch_attribute
        self._mock_callable_after_functions = []

        def register_assertion(assertion):
            if self._example.is_async:

                async def f(_):
                    assertion()

            else:
                f = lambda _: assertion()
            self._mock_callable_after_functions.append(f)

        testslide.mock_callable.register_assertion = register_assertion

    def __init__(self, example):
        self._example = example
        self._context = example.context
        self._after_functions = []
        self._test_case = unittest.TestCase()
        self._init_sub_example()
        self._init_mocks()

    @staticmethod
    def _not_callable(self):
        raise BaseException("This function should not be called outside test code.")

    @property
    def _all_methods(self):
        return self._context.all_context_data_methods

    @property
    def _all_attributes(self):
        return self._context.all_context_data_memoizable_attributes

    def __getattr__(self, name):
        if name in self._all_methods.keys():

            def static(*args, **kwargs):
                return self._all_methods[name](self, *args, **kwargs)

            self.__dict__[name] = static

        if name in self._all_attributes.keys():
            attribute_code = self._all_attributes[name]
            if self._example.is_async and inspect.iscoroutinefunction(attribute_code):
                raise ValueError(
                    f"Function can not be a coroutine function: {repr(attribute_code)}"
                )
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

    def after(self, after_code):
        """
        Use this to decorate a function to be registered to be executed after
        the example code.
        """
        self._after_functions.append(after_code)
        return self._not_callable

    @contextmanager
    def sub_example(self, name=None):
        """
        Use this as a context manager many times inside the same
        example. Failures in the code inside the context manager
        will be aggregated, and reported individually at the end.
        """
        with self._sub_examples_agg_ex.catch():
            yield


class AggregatedExceptions(Exception):
    """
    Aggregate example execution exceptions.
    """

    def __init__(self):
        super(AggregatedExceptions, self).__init__()
        self.exceptions = []

    def append_exception(self, exception):
        if isinstance(exception, AggregatedExceptions):
            self.exceptions.extend(exception.exceptions)
        else:
            self.exceptions.append(exception)

    @contextmanager
    def catch(self):
        try:
            yield
        except BaseException as exception:
            self.append_exception(exception)

    def __str__(self):
        return "{} failures.\n".format(len(self.exceptions)) + "\n".join(
            f"{type(e)}: {str(e)}" for e in self.exceptions
        )

    def raise_correct_exception(self):
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


class _ExampleRunner:
    def __init__(self, example):
        self.example = example

    @staticmethod
    async def _fail_if_not_coroutine_function(func, *args, **kwargs):
        if not inspect.iscoroutinefunction(func):
            raise ValueError(f"Function must be a coroutine function: {repr(func)}")
        return await func(*args, **kwargs)

    async def _real_async_run_all_hooks_and_example(
        self, context_data, around_functions=None
    ):
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
            aggregated_exceptions = AggregatedExceptions()
            with aggregated_exceptions.catch():
                for before_code in self.example.context.all_before_functions:
                    await self._fail_if_not_coroutine_function(
                        before_code, context_data
                    )
                await self._fail_if_not_coroutine_function(
                    self.example.code, context_data
                )
            after_functions = []
            after_functions.extend(context_data._mock_callable_after_functions)
            after_functions.extend(self.example.context.all_after_functions)
            after_functions.extend(context_data._after_functions)
            for after_code in reversed(after_functions):
                with aggregated_exceptions.catch():
                    await self._fail_if_not_coroutine_function(after_code, context_data)
            aggregated_exceptions.raise_correct_exception()
            return
        around_code = around_functions.pop()

        wrapped_called = []

        async def async_wrapped():
            wrapped_called.append(True)
            await self._real_async_run_all_hooks_and_example(
                context_data, around_functions
            )

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
    def _raise_if_asyncio_warnings(self, context_data):
        if sys.version_info < (3, 7):
            yield
            return
        original_showwarning = warnings.showwarning
        caught_failures = []

        def showwarning(message, category, filename, lineno, file=None, line=None):
            failure_warning_messages = {
                RuntimeWarning: "^coroutine '.+' was never awaited"
            }
            warning_class = type(message)
            pattern = failure_warning_messages.get(warning_class, None)
            if pattern and re.compile(pattern).match(str(message)):
                caught_failures.append(message)
            else:
                original_showwarning(message, category, filename, lineno, file, line)

        warnings.showwarning = showwarning

        original_logger_warning = asyncio.log.logger.warning

        def logger_warning(msg, *args, **kwargs):
            if re.compile("^Executing .+ took .+ seconds$").match(str(msg)):
                msg = (
                    f"{msg}\n"
                    "During the execution of the async test a slow callback "
                    "that blocked the event loop was detected.\n"
                    "Tip: you can customize the detection threshold with:\n"
                    "  asyncio.get_running_loop().slow_callback_duration = seconds"
                )
                caught_failures.append(SlowCallback(msg % args))
            else:
                original_logger_warning(msg, *args, **kwargs)

        asyncio.log.logger.warning = logger_warning

        aggregated_exceptions = AggregatedExceptions()

        try:
            with aggregated_exceptions.catch():
                yield
        finally:
            warnings.showwarning = original_showwarning
            asyncio.log.logger.warning = original_logger_warning
            for failure in caught_failures:
                with aggregated_exceptions.catch():
                    raise failure
            aggregated_exceptions.raise_correct_exception()

    def _async_run_all_hooks_and_example(self, context_data):
        coro = self._real_async_run_all_hooks_and_example(context_data)
        with self._raise_if_asyncio_warnings(context_data):
            if sys.version_info < (3, 7):
                loop = asyncio.events.new_event_loop()
                try:
                    loop.set_debug(True)
                    loop.run_until_complete(coro)
                finally:
                    try:
                        loop.run_until_complete(loop.shutdown_asyncgens())
                    finally:
                        loop.close()
            else:
                asyncio.run(coro, debug=True)

    @staticmethod
    def _fail_if_coroutine_function(func, *args, **kwargs):
        if inspect.iscoroutinefunction(func):
            raise ValueError(f"Function can not be a coroutine function: {repr(func)}")
        return func(*args, **kwargs)

    def _sync_run_all_hooks_and_example(self, context_data, around_functions=None):
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
            aggregated_exceptions = AggregatedExceptions()
            with aggregated_exceptions.catch():
                for before_code in self.example.context.all_before_functions:
                    self._fail_if_coroutine_function(before_code, context_data)
                self._fail_if_coroutine_function(self.example.code, context_data)
            after_functions = []
            after_functions.extend(context_data._mock_callable_after_functions)
            after_functions.extend(self.example.context.all_after_functions)
            after_functions.extend(context_data._after_functions)
            for after_code in reversed(after_functions):
                with aggregated_exceptions.catch():
                    self._fail_if_coroutine_function(after_code, context_data)
            aggregated_exceptions.raise_correct_exception()
            return
        around_code = around_functions.pop()

        wrapped_called = []

        def wrapped():
            wrapped_called.append(True)
            self._sync_run_all_hooks_and_example(context_data, around_functions)

        self._fail_if_coroutine_function(around_code, context_data, wrapped)

        if not wrapped_called:
            raise RuntimeError(
                "Around hook "
                + repr(around_code.__name__)
                + " did not execute example code!"
            )

    def run(self):
        try:
            if self.example.skip:
                raise Skip()
            context_data = _ContextData(self.example)
            if self.example.is_async:
                self._async_run_all_hooks_and_example(context_data)
            else:
                self._sync_run_all_hooks_and_example(context_data)
        finally:
            sys.stdout.flush()
            sys.stderr.flush()
            testslide.mock_callable.unpatch_all_callable_mocks()
            testslide.mock_constructor.unpatch_all_constructor_mocks()
            testslide.patch_attribute.unpatch_all_mocked_attributes()


class Example(object):
    """
    Individual example.
    """

    def __init__(self, name, code, context, skip=False, focus=False):
        self.name = name
        self.code = code
        self.is_async = inspect.iscoroutinefunction(self.code)
        self.context = context
        self.__dict__["skip"] = skip
        self.__dict__["focus"] = focus

    @property
    def full_name(self):
        return "{context_full_name}: {example_name}".format(
            context_full_name=self.context.full_name, example_name=self.name
        )

    @property
    def skip(self):
        """
        True if the example of its context is marked to be skipped.
        """
        return any([self.context.skip, self.__dict__["skip"]])

    @property
    def focus(self):
        """
        True if the example of its context is marked to be focused.
        """
        return any([self.context.focus, self.__dict__["focus"]])

    def __call__(self):
        """
        Run the example, including all around, before and after hooks.
        """
        _ExampleRunner(self).run()

    def __str__(self):
        return self.name


class _TestSlideTestResult(unittest.TestResult):
    """
    Concrete unittest.TestResult to allow unttest.TestCase integration, by
    aggregating failures at an AggregatedExceptions instance.
    """

    def __init__(self):
        super(_TestSlideTestResult, self).__init__()
        self.aggregated_exceptions = AggregatedExceptions()

    def _add_exception(self, err):
        exc_type, exc_value, exc_traceback = err
        self.aggregated_exceptions.append_exception(exc_value)

    def addError(self, test, err):
        """Called when an error has occurred. 'err' is a tuple of values as
        returned by sys.exc_info().
        """
        super(_TestSlideTestResult, self).addError(test, err)
        self._add_exception(err)

    def addFailure(self, test, err):
        """Called when an error has occurred. 'err' is a tuple of values as
        returned by sys.exc_info()."""
        super(_TestSlideTestResult, self).addFailure(test, err)
        self._add_exception(err)

    def addSkip(self, test, reason):
        """Called when the test case test is skipped. reason is the reason
        the test gave for skipping."""
        super(_TestSlideTestResult, self).addSkip(test, reason)
        self._add_exception((type(Skip), Skip(), None))

    def addUnexpectedSuccess(self, test):
        """Called when the test case test was marked with the expectedFailure()
        decorator, but succeeded."""
        super(_TestSlideTestResult, self).addUnexpectedSuccess(test)
        self._add_exception((type(UnexpectedSuccess), UnexpectedSuccess(), None))

    def addSubTest(self, test, subtest, err):
        """Called at the end of a subtest.
        'err' is None if the subtest ended successfully, otherwise it's a
        tuple of values as returned by sys.exc_info().
        """
        super(_TestSlideTestResult, self).addSubTest(test, subtest, err)
        if err:
            self._add_exception(err)


class Context(object):
    """
    Container for example contexts.
    """

    _SAME_CONTEXT_NAME_ERROR = "A context with the same name is already defined"

    # List of all top level contexts created
    all_top_level_contexts = []

    # Constructor

    def __init__(
        self, name, parent_context=None, shared=False, skip=False, focus=False
    ):
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

        self.name = name
        self.parent_context = parent_context
        self.shared = shared
        self.__dict__["skip"] = skip
        self.__dict__["focus"] = focus
        self.children_contexts = []
        self.examples = []
        self.before_functions = []
        self.after_functions = []
        self.around_functions = []
        self.context_data_methods = {}
        self.context_data_memoizable_attributes = {}
        self.shared_contexts = {}
        self._runtime_attributes = []

        if not self.parent_context and not self.shared:
            self.all_top_level_contexts.append(self)

    # Properties

    @property
    def parent_contexts(self):
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
    def depth(self):
        """
        Number of parent contexts this context has.
        """
        return len(self.parent_contexts)

    def _all_parents_as_dict(original):  # noqa: B902
        """
        Use as a decorator for empty functions named all_attribute_name, to make
        them return a dict with self.parent_context.all_attribute_name and
        self.attribute_name.
        """

        def get_all(self):
            final_dict = {}
            if self.parent_context:
                final_dict.update(getattr(self.parent_context, original.__name__))
            final_dict.update(getattr(self, original.__name__.split("all_")[1]))
            return final_dict

        return get_all

    def _all_parents_as_list(original):  # noqa: B902
        """
        Use as a decorator for empty functions named all_attribute_name, to make
        them return a list with self.parent_context.all_attribute_name and
        self.attribute_name.
        """

        def get_all(self):
            final_list = []
            if self.parent_context:
                final_list.extend(getattr(self.parent_context, original.__name__))
            final_list.extend(getattr(self, original.__name__.split("all_")[1]))
            return final_list

        return get_all

    @property  # type: ignore
    @_all_parents_as_dict
    def all_context_data_methods(self):
        """
        Returns a combined dict of all context_data_methods, including from
        parent contexts.
        """
        pass

    @property  # type: ignore
    @_all_parents_as_dict
    def all_context_data_memoizable_attributes(self):
        """
        Returns a combined dict of all context_data_memoizable_attributes,
        including from parent contexts.
        """
        pass

    @property  # type: ignore
    @_all_parents_as_list
    def all_around_functions(self):
        """
        Return a list of all around_functions, including from parent contexts.
        """
        pass

    @property  # type: ignore
    @_all_parents_as_list
    def all_before_functions(self):
        """
        Return a list of all before_functions, including from parent contexts.
        """
        pass

    @property  # type: ignore
    @_all_parents_as_list
    def all_after_functions(self):
        """
        Return a list of all after_functions, including from parent contexts.
        """
        pass

    @property  # type: ignore
    @_all_parents_as_dict
    def all_shared_contexts(self):
        """
        Returns a combined dict of all shared_contexts, including from parent
        contexts.
        """
        pass

    @property
    def all_examples(self):
        """
        List of of all examples in this context and nested contexts.
        """
        final_list = []
        final_list.extend(self.examples)
        for child_context in self.children_contexts:
            final_list.extend(child_context.all_examples)
        return final_list

    @property
    def hierarchy(self):
        """
        Returns a list of all contexts in this hierarchy.
        """
        return [context for context in list(reversed(self.parent_contexts)) + [self]]

    @property
    def full_name(self):
        """
        Full context name, including parent contexts.
        """
        return ", ".join(str(context) for context in self.hierarchy)

    @property
    def skip(self):
        """
        True if this context of any parent context are tagged to be skipped.
        """
        return any(context.__dict__["skip"] for context in self.hierarchy)

    @property
    def focus(self):
        """
        True if this context of any parent context are tagged to be focused.
        """
        return any(context.__dict__["focus"] for context in self.hierarchy)

    def __str__(self):
        return self.name

    def add_child_context(self, name, skip=False, focus=False):
        """
        Creates a nested context below self.
        """
        if name in [context.name for context in self.children_contexts]:
            raise RuntimeError(self._SAME_CONTEXT_NAME_ERROR)

        child_context = Context(name, parent_context=self, skip=skip, focus=focus)
        self.children_contexts.append(child_context)
        return child_context

    def add_example(self, name, example_code, skip=False, focus=False):
        """
        Add an example to this context.
        """
        if name in [example.name for example in self.examples]:
            raise RuntimeError("An example with the same name is already defined")

        self.examples.append(
            Example(name, code=example_code, context=self, skip=skip, focus=focus)
        )

        return self.examples[-1]

    def has_attribute(self, name):
        return any(
            [
                name in self.context_data_methods.keys(),
                name in self.context_data_memoizable_attributes.keys(),
                name in self._runtime_attributes,
            ]
        )

    def add_function(self, name, function_code):
        """
        Add given function to example execution scope.
        """
        if self.has_attribute(name):
            raise AttributeError(
                'Attribute "{}" already set for context "{}"'.format(name, self)
            )
        self.context_data_methods[name] = function_code

    def register_runtime_attribute(self, name):
        """
        Register name as a new runtime attribute, that can not be registered
        again.
        """
        if name in self._runtime_attributes:
            raise AttributeError(
                'Attribute "{}" already set for context "{}"'.format(name, self)
            )
        self._runtime_attributes.append(name)

    def add_memoized_attribute(self, name, memoizable_code):
        """
        Add given attribute name to execution scope, by lazily memoizing the return
        value of memoizable_code().
        """
        if self.has_attribute(name):
            raise AttributeError(
                'Attribute "{}" already set for context "{}"'.format(name, self)
            )
        self.context_data_memoizable_attributes[name] = memoizable_code

    def add_shared_context(self, name, shared_context_code):
        """
        Create a shared context.
        """
        if name in self.shared_contexts:
            raise RuntimeError("A shared context with the same name is already defined")
        self.shared_contexts[name] = shared_context_code

    def add_test_case(self, test_case, attr_name):
        """
        Add around hooks to context from given unittest.TestCase class. Only
        hooks such as setUp or tearDown will be called, no tests will be
        included.
        """

        def wrap_test_case(self, example):
            def test_test_slide(_):
                example()

            def exec_body(ns):
                ns.update({"test_test_slide": test_test_slide})

            # Build a child class of given TestCase, with a defined test that
            # will run TestSlide example.
            test_slide_test_case = types.new_class(
                "TestSlideTestCase", bases=(test_case,), exec_body=exec_body
            )

            # This suite will only contain TestSlide's example test.
            test_suite = unittest.TestLoader().loadTestsFromName(
                "test_test_slide", test_slide_test_case
            )
            setattr(self, attr_name, list(test_suite)[0])
            result = _TestSlideTestResult()
            test_suite(result=result)
            if not result.wasSuccessful():
                result.aggregated_exceptions.raise_correct_exception()

        self.around_functions.append(wrap_test_case)


def reset():
    """
    Clear all defined contexts and hooks.
    """
    Context.all_top_level_contexts.clear()


class TestCase(unittest.TestCase):
    """
    A subclass of unittest.TestCase that adds TestSlide's features.
    """

    def setUp(self):
        testslide.mock_callable.register_assertion = lambda assertion: self.addCleanup(
            assertion
        )
        self.addCleanup(testslide.mock_callable.unpatch_all_callable_mocks)
        self.addCleanup(testslide.mock_constructor.unpatch_all_constructor_mocks)
        self.addCleanup(testslide.patch_attribute.unpatch_all_mocked_attributes)
        super(TestCase, self).setUp()

    @staticmethod
    def mock_callable(*args, **kwargs):
        return testslide.mock_callable.mock_callable(*args, **kwargs)

    @staticmethod
    def mock_async_callable(*args, **kwargs):
        return testslide.mock_callable.mock_async_callable(*args, **kwargs)

    @staticmethod
    def mock_constructor(*args, **kwargs):
        return testslide.mock_constructor.mock_constructor(*args, **kwargs)

    @staticmethod
    def patch_attribute(*args, **kwargs):
        return testslide.patch_attribute.patch_attribute(*args, **kwargs)
