# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from contextlib import contextmanager

from typing import List  # noqa
import sys
import unittest
import re
import types

import testslide.mock_callable
import testslide.mock_constructor
from testslide.strict_mock import StrictMock

if sys.version_info[0] >= 3:
    from contextlib import redirect_stdout, redirect_stderr
else:

    @contextmanager
    def redirect_stdout(target):
        original = sys.stdout
        sys.stdout = target
        try:
            yield
        finally:
            sys.stdout = original

    @contextmanager
    def redirect_stderr(target):
        original = sys.stderr
        sys.stderr = target
        try:
            yield
        finally:
            sys.stderr = original


@contextmanager
def _add_traceback_context_manager():
    """
    Add __traceback__ to exceptions raised within the block, to give Python
    2 compatibility.
    """
    if sys.version_info[0] == 2:
        try:
            yield
        except BaseException as e:
            _exc_type, _exc_value, exc_traceback = sys.exc_info()
            e.__dict__["__traceback__"] = exc_traceback
            raise e
    else:
        yield


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

    def __init__(self, context):
        self.context = context
        self.after_functions = []
        # The use of methodName parameter is required as a placeholder for
        # Python 2 compatibility only.
        method_name = "assertEqual"
        self._test_case = unittest.TestCase(methodName=method_name)
        self._sub_examples_agg_ex = AggregatedExceptions()

        def assert_sub_examples(self):
            if self._sub_examples_agg_ex.exceptions:
                self._sub_examples_agg_ex.raise_correct_exception()

        self.after(assert_sub_examples)

    @staticmethod
    def _not_callable(self):
        raise BaseException("This function should not be called outside test code.")

    @property
    def _all_methods(self):
        return self.context.all_context_data_methods

    @property
    def _all_attributes(self):
        return self.context.all_context_data_memoizable_attributes

    def __getattr__(self, name):
        if name in self._all_methods.keys():

            def static(*args, **kwargs):
                return self._all_methods[name](self, *args, **kwargs)

            self.__dict__[name] = static

        if name in self._all_attributes.keys():
            self.__dict__[name] = self._all_attributes[name](self)

        try:
            return self.__dict__[name]
        except KeyError:
            # Forward assert* methods to unittest.TestCase
            if re.match("^assert", name) and hasattr(self._test_case, name):
                return getattr(self._test_case, name)
            raise AttributeError(
                "Context '{}' has no attribute '{}'".format(self.context, name)
            )

    def after(self, after_code):
        """
        Use this to decorate a function to be registered to be executed after
        the example code.
        """
        self.after_functions.append(after_code)
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
            with _add_traceback_context_manager():
                yield
        except BaseException as exception:
            self.append_exception(exception)

    def __str__(self):
        return "{} failures.".format(len(self.exceptions))

    def raise_correct_exception(self):
        if not self.exceptions:
            return
        ex_types = {type(ex) for ex in self.exceptions}
        if Skip in ex_types or unittest.SkipTest in ex_types:
            raise Skip()
        else:
            raise self


class Skip(Exception):
    """
    Raised by an example when it is skipped
    """

    pass


class Example(object):
    """
    Individual example.
    """

    def __init__(self, name, code, context, skip=False, focus=False):
        self.name = name
        self.code = code
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

    @contextmanager
    def execute_around_hooks(self, context_data):
        around_generators = [
            around(context_data) for around in self.context.all_around_functions
        ]

        for around_generator in reversed(around_generators):
            next(around_generator)

        yield

        for around_generator in around_generators:
            try:
                next(around_generator)
            except StopIteration:
                pass

    def _example_runner(self, context_data):
        """
        Execute before hooks, example and after hooks.
        """
        aggregated_exceptions = AggregatedExceptions()
        with aggregated_exceptions.catch():
            for before in self.context.all_before_functions:
                before(context_data)
            self.code(context_data)
        after_functions = []
        after_functions.extend(self.context.all_after_functions)
        after_functions.extend(context_data.after_functions)
        for after in reversed(after_functions):
            with aggregated_exceptions.catch():
                after(context_data)
        for assertion in self.context.assertions:
            with aggregated_exceptions.catch():
                assertion()
        if aggregated_exceptions.exceptions:
            aggregated_exceptions.raise_correct_exception()

    def _run_example(self, around_functions, context_data):
        """
        Run example, including all hooks.
        """
        if not around_functions:
            self._example_runner(context_data)
            return
        around = around_functions.pop()

        def wrapped():
            self._run_example(around_functions, context_data)

        around(context_data, wrapped)

    def __call__(self):
        """
        Run the example, including all around, before and after hooks.
        """
        try:
            if self.skip:
                raise Skip()
            _run_before_once_hooks()
            context_data = _ContextData(self.context)
            with _add_traceback_context_manager():
                self._run_example(
                    list(reversed(self.context.all_around_functions)), context_data
                )
        finally:
            sys.stdout.flush()
            sys.stderr.flush()
            testslide.mock_callable.unpatch_all_callable_mocks()
            testslide.mock_constructor.unpatch_all_constructor_mocks()

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
        # Decorate __traceback__ for Python 2 compatibility
        if sys.version_info[0] == 2:
            exc_value.__dict__["__traceback__"] = err[2]
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
    all_top_level_contexts = []  # type: List[Context]

    def _setup_mock_callable(self):
        def _mock_callable(self, *args, **kwargs):
            return testslide.mock_callable.mock_callable(*args, **kwargs)

        self.add_function("mock_callable", _mock_callable)

        def register_assertion(assertion):
            self.assertions.append(assertion)

        testslide.mock_callable.register_assertion = register_assertion

    def _setup_mock_constructor(self):
        def _mock_constructor(self, *args, **kwargs):
            return testslide.mock_constructor.mock_constructor(*args, **kwargs)

        self.add_function("mock_constructor", _mock_constructor)

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
        self.assertions = []
        self.around_functions = []
        self.context_data_methods = {}
        self.context_data_memoizable_attributes = {}
        self.shared_contexts = {}
        self._runtime_attributes = []

        if not self.parent_context and not self.shared:
            self.all_top_level_contexts.append(self)

        self._setup_mock_callable()
        self._setup_mock_constructor()

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

    def _context_data_has_attr(self, name):
        return any(
            [
                name in self.context_data_methods.keys(),
                name in self.context_data_memoizable_attributes.keys(),
            ]
        )

    def add_function(self, name, function_code):
        """
        Add given function to example execution scope.
        """
        if self._context_data_has_attr(name):
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
        if self._context_data_has_attr(name):
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
            if sys.version_info[0] == 2:
                test_slide_test_case = type(
                    str("TestSlideTestCase"),
                    (test_case,),
                    {"test_test_slide": test_test_slide},
                )
            else:
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


before_once_functions = []  # type: List[function]
before_once_executed = False


def _run_before_once_hooks():
    global before_once_executed
    if not before_once_executed:
        global before_once_functions
        with _add_traceback_context_manager():
            for code in before_once_functions:
                code()
        before_once_executed = True


def reset():
    """
    Clear all defined contexts and hooks.
    """
    if sys.version_info[0] >= 3:
        Context.all_top_level_contexts.clear()
    else:
        Context.all_top_level_contexts[:] = []
    global before_once_functions
    if sys.version_info[0] >= 3:
        before_once_functions.clear()
    else:
        before_once_functions[:] = []
    global before_once_executed
    before_once_executed = False


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
        super(TestCase, self).setUp()

    mock_callable = staticmethod(testslide.mock_callable.mock_callable)

    mock_constructor = staticmethod(testslide.mock_constructor.mock_constructor)


def _test_function(arg1, arg2, kwarg1=None, kwarg2=None):
    "This function is used by some unit tests only"
    return "original response"
