# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import testslide
from testslide.dsl import context, xcontext, fcontext, Skip  # noqa: F401

from testslide.mock_callable import (
    mock_callable,
    UndefinedBehaviorForCall,
    UnexpectedCallReceived,
    UnexpectedCallArguments,
)
import contextlib
from testslide.strict_mock import StrictMock
import sys
import time
import os


class TargetStr(object):
    def __str__(self):
        return "original response"


class ParentTarget(TargetStr):
    def instance_method(self, arg1, arg2, kwarg1=None, kwarg2=None):
        return "original response"

    @staticmethod
    def static_method(arg1, arg2, kwarg1=None, kwarg2=None):
        return "original response"

    @classmethod
    def class_method(cls, arg1, arg2, kwarg1=None, kwarg2=None):
        return "original response"


class Target(ParentTarget):
    def __init__(self):
        self.dynamic_instance_method = (
            lambda arg1, arg2, kwarg1=None, kwarg2=None: "original response"
        )
        super(Target, self).__init__()

    @property
    def invalid(self):
        """
        Covers a case where create_autospec at an instance would fail.
        """
        raise RuntimeError("Should not be accessed")


@context("mock_callable(target, callable)")  # noqa: C901
def mock_callable_context(context):

    ##
    ## Common mock_callable setup
    ##

    context.memoize("assertions", lambda _: [])
    context.memoize("call_args", lambda _: ("first", "second"))
    context.memoize("call_kwargs", lambda _: {"kwarg1": "first", "kwarg2": "second"})

    @context.memoize
    def specific_call_args(self):
        return tuple("specific {}".format(arg) for arg in self.call_args)

    @context.memoize
    def specific_call_kwargs(self):
        return {k: "specific {}".format(v) for k, v in self.call_kwargs.items()}

    @context.before
    def register_assertions(self):
        def register_assertion(assertion):
            self.assertions.append(assertion)

        testslide.mock_callable.register_assertion = register_assertion

    @context.after
    def cleanup_patches(self):
        # Unpatch before assertions, to make sure it is done if assertion fails.
        testslide.mock_callable.unpatch_all_callable_mocks()
        for assertion in self.assertions:
            assertion()

    @context.function
    @contextlib.contextmanager
    def assertRaisesWithMessage(self, exception, msg):
        with self.assertRaises(exception) as cm:
            yield
        ex_msg = str(cm.exception)
        self.assertEqual(
            ex_msg,
            msg,
            "Expected exception {}.{} message "
            "to be\n{}\nbut got\n{}.".format(
                exception.__module__, exception.__name__, repr(msg), repr(ex_msg)
            ),
        )

    @context.shared_context
    def examples_for_target(
        context,
        callable_accepts_no_args=False,
        has_original_callable=True,
        can_yield=True,
        validate_signature=True,
    ):
        @context.function
        def assert_all(self):
            try:
                for assertion in self.assertions:
                    assertion()
            finally:
                del self.assertions[:]

        @context.function
        def no_behavior_msg(self):
            if self.call_args:
                args_msg = "    {}\n".format(self.call_args)
            else:
                args_msg = ""
            if self.call_kwargs:
                kwargs_msg = (
                    "    {\n"
                    + "".join(
                        "      {}={},\n".format(k, self.call_kwargs[k])
                        for k in sorted(self.call_kwargs.keys())
                    )
                    + "    }\n"
                )
            else:
                kwargs_msg = ""
            return str(
                "{}, {}:\n".format(repr(self.target_arg), repr(self.callable_arg))
                + "  Received call:\n"
                + args_msg
                + kwargs_msg
                + "  But no behavior was defined for it."
            )

        @context.shared_context
        def mock_call_arguments(context):
            @context.example
            def works_for_matching_signature(self):
                self.callable_target(*self.call_args, **self.call_kwargs),

            if validate_signature and sys.version_info[0] != 2:

                @context.example
                def raises_TypeError_for_mismatching_signature(self):
                    args = ("some", "invalid", "args", "list")
                    kwargs = {"invalid_kwarg": "invalid_value"}
                    with self.assertRaises(TypeError):
                        self.callable_target(*args, **kwargs)

            @context.sub_context(".for_call(*args, **kwargs)")
            def for_call_args_kwargs(context):

                if not callable_accepts_no_args:

                    @context.sub_context
                    def with_matching_signature(context):
                        @context.before
                        def before(self):
                            self.mock_callable_dsl.for_call(
                                *self.specific_call_args, **self.specific_call_kwargs
                            )

                        @context.example
                        def it_accepts_known_arguments(self):
                            self.callable_target(
                                *self.specific_call_args, **self.specific_call_kwargs
                            )

                        if validate_signature:

                            @context.example
                            def it_rejects_unknown_arguments(self):
                                with self.assertRaisesWithMessage(
                                    UnexpectedCallArguments,
                                    self.no_behavior_msg()
                                    + "\n  These are the registered calls:\n"
                                    + "    {}\n".format(self.specific_call_args)
                                    + "    {\n"
                                    + "".join(
                                        "      {}={},\n".format(
                                            k, self.specific_call_kwargs[k]
                                        )
                                        for k in sorted(
                                            self.specific_call_kwargs.keys()
                                        )
                                    )
                                    + "    }\n",
                                ):
                                    self.callable_target(
                                        *self.call_args, **self.call_kwargs
                                    )

                    if validate_signature:

                        @context.sub_context
                        def with_mismatching_signature(context):
                            @context.xexample
                            def it_fails_to_mock(self):
                                with self.assertRaisesWithMessage(
                                    ValueError,
                                    "Can not mock target for arguments that mismatch the "
                                    "original callable signature.",
                                ):
                                    self.mock_callable_dsl.for_call(
                                        "some",
                                        "invalid",
                                        "args",
                                        and_some="invalid",
                                        kwargs="values",
                                    )

        @context.shared_context
        def assertions(context):
            @context.shared_context
            def assert_failure(context):
                @context.after
                def after(self):
                    with self.assertRaises(AssertionError):
                        self.assert_all()

            @context.shared_context
            def not_called(context):
                @context.example
                def not_called(self):
                    pass

            @context.shared_context
            def called_less_times(context):
                @context.example
                def called_less_times(self):
                    for _ in range(self.times - 1):
                        self.callable_target(*self.call_args, **self.call_kwargs)

            @context.shared_context
            def called_more_times(context):
                @context.example
                def called_more_times(self):
                    for _ in range(self.times + 1):
                        self.callable_target(*self.call_args, **self.call_kwargs)

            @context.shared_context
            def called_more_times_fail(context):
                @context.example
                def called_more_times(self):
                    for _ in range(self.times):
                        self.callable_target(*self.call_args, **self.call_kwargs)
                    with self.assertRaisesWithMessage(
                        UnexpectedCallReceived,
                        (
                            "Unexpected call received.\n"
                            "{}, {}:\n"
                            "  expected to receive at most {} calls with any arguments "
                            "  but received an extra call."
                        ).format(
                            repr(self.target_arg), repr(self.callable_arg), self.times
                        ),
                    ):
                        self.callable_target(*self.call_args, **self.call_kwargs)

            @context.shared_context
            def called_exactly_times(context):
                @context.example
                def called_exactly_times(self):
                    for _ in range(self.times):
                        self.callable_target(*self.call_args, **self.call_kwargs)

            @context.sub_context(".and_assert_called_exactly(times)")
            def and_assert_called_exactly(context):
                @context.sub_context
                def with_valid_input(context):
                    @context.before
                    def setup_assertion(self):
                        self.mock_callable_dsl.and_assert_called_exactly(self.times)

                    @context.sub_context
                    def fails_when(context):

                        context.merge_context("assert failure")

                        context.merge_context("not called")
                        context.merge_context("called less times")
                        context.merge_context("called more times fail")

                    @context.sub_context
                    def passes_when(context):

                        context.merge_context("called exactly times")

            @context.sub_context(".and_assert_called_at_least(times)")
            def and_assert_called_at_least(context):
                @context.sub_context
                def with_invalid_input(context):
                    @context.example("fails to mock when times < 1")
                    def fails_to_mock_when_times_1(self):
                        with self.assertRaisesWithMessage(
                            ValueError, "times must be >= 1"
                        ):
                            self.mock_callable_dsl.and_assert_called_at_least(0)

                @context.sub_context
                def with_valid_input(context):
                    @context.before
                    def setup_assertion(self):
                        self.mock_callable_dsl.and_assert_called_at_least(self.times)

                    @context.sub_context
                    def fails_when(context):

                        context.merge_context("assert failure")

                        context.merge_context("not called")
                        context.merge_context("called less times")

                    @context.sub_context
                    def passes_when(context):

                        context.merge_context("called exactly times")
                        context.merge_context("called more times")

            @context.sub_context(".and_assert_called_at_most(times)")
            def and_assert_called_at_most(context):
                @context.sub_context
                def with_invalid_input(context):
                    @context.example("fails to mock when times < 1")
                    def fails_to_mock_when_times_1(self):
                        with self.assertRaisesWithMessage(
                            ValueError, "times must be >= 1"
                        ):
                            self.mock_callable_dsl.and_assert_called_at_most(0)

                @context.sub_context
                def with_valid_input(context):
                    @context.before
                    def setup_assertion(self):
                        self.mock_callable_dsl.and_assert_called_at_most(self.times)

                    @context.sub_context
                    def fails_when(context):

                        context.merge_context("assert failure")

                        context.merge_context("not called")
                        context.merge_context("called more times fail")

                    @context.sub_context
                    def passes_when(context):

                        context.merge_context("called less times")
                        context.merge_context("called exactly times")

            @context.sub_context(".and_assert_called()")
            def and_assert_called(context):
                @context.before
                def setup_assertion(self):
                    self.mock_callable_dsl.and_assert_called()

                @context.sub_context
                def fails_when(context):

                    context.merge_context("assert failure")

                    context.merge_context("not called")

                @context.sub_context
                def passes_when(context):
                    @context.example
                    def called_once(self):
                        self.callable_target(*self.call_args, **self.call_kwargs)

                    @context.example
                    def called_several_times(self):
                        for _ in range(self.times + 1):
                            self.callable_target(*self.call_args, **self.call_kwargs)

            @context.sub_context(".and_assert_not_called()")
            def and_assert_not_called(context):
                @context.example
                def can_use_with_previously_existing_behavior(self):
                    self.mock_callable_dsl.and_assert_not_called()

        @context.sub_context
        def default_behavior(context):
            @context.example
            def mock_call_fails_with_undefined_behavior(self):
                with self.assertRaisesWithMessage(
                    UndefinedBehaviorForCall, self.no_behavior_msg()
                ):
                    self.callable_target(*self.call_args, **self.call_kwargs)

            @context.sub_context(".and_assert_not_called()")
            def and_assert_not_called(context):
                @context.before
                def setup_assertion(self):
                    self.mock_callable_dsl.and_assert_not_called()

                @context.sub_context
                def passes_when(context):
                    @context.example
                    def not_called(self):
                        pass

                @context.sub_context
                def fails_when(context):
                    @context.after
                    def after(self):
                        with self.assertRaises(AssertionError):
                            self.assert_all()

                    @context.example
                    def called(self):
                        with self.assertRaisesWithMessage(
                            UnexpectedCallReceived,
                            "{}, {}: Excepted not to be called!".format(
                                repr(self.real_target), repr(self.callable_arg)
                            ),
                        ):
                            self.callable_target(*self.call_args, **self.call_kwargs)

        @context.sub_context(".to_return(value)")
        def to_return_value(context):

            context.memoize("value", lambda _: "mocked value")
            context.memoize("times", lambda _: 3)

            @context.before
            def setup_mock(self):
                self.mock_callable_dsl.to_return_value(self.value)

            if has_original_callable:
                context.nest_context("mock call arguments")
            context.nest_context("assertions")

            @context.example
            def mock_call_returns_given_value(self):
                self.assertEqual(
                    self.callable_target(*self.call_args, **self.call_kwargs),
                    self.value,
                )
                other_args = ["other_arg" for arg in self.call_args]
                other_kwargs = {k: "other_value" for k in self.call_kwargs}
                self.assertEqual(
                    self.callable_target(*other_args, **other_kwargs), self.value
                )

        @context.sub_context(".to_return_values(values_list)")
        def to_return_values_values_list(context):

            context.memoize("values_list", lambda _: ["first", "second", "third"])
            context.memoize("times", lambda self: len(self.values_list) - 1)

            @context.before
            def setup_mock(self):
                self.mock_callable_dsl.to_return_values(self.values_list)

            if has_original_callable:
                context.nest_context("mock call arguments")
            context.nest_context("assertions")

            @context.example
            def return_values_from_list_in_order(self):
                for value in self.values_list:
                    self.assertEqual(
                        self.callable_target(*self.call_args, **self.call_kwargs), value
                    )

            @context.sub_context
            def when_list_is_exhausted(context):
                @context.before
                def before(self):
                    for _ in self.values_list:
                        self.callable_target(*self.call_args, **self.call_kwargs)

                @context.example
                def it_raises(self):
                    with self.assertRaisesWithMessage(
                        UndefinedBehaviorForCall, "No more values to return!"
                    ):
                        self.callable_target(*self.call_args, **self.call_kwargs)

        if can_yield:

            @context.sub_context(".to_yield_values(values_list)")
            def to_yield_values_values_list(context):

                context.memoize("values_list", lambda _: ["first", "second", "third"])
                context.memoize("times", lambda self: len(self.values_list) - 1)

                @context.before
                def setup_mock(self):
                    self.mock_callable_dsl.to_yield_values(self.values_list)

                if has_original_callable:
                    context.nest_context("mock call arguments")
                context.nest_context("assertions")

                @context.memoize
                def iterable(self):
                    return iter(
                        self.callable_target(*self.call_args, **self.call_kwargs)
                    )

                @context.example
                def yield_values_from_list_in_order(self):
                    for value in self.values_list:
                        self.assertEqual(next(self.iterable), value)

                @context.sub_context
                def when_list_is_empty(context):
                    @context.before
                    def before(self):
                        for _ in self.values_list:
                            next(self.iterable)

                    @context.example
                    def it_raises_StopIteration(self):
                        with self.assertRaises(StopIteration):
                            next(self.iterable)

        @context.sub_context(".to_raise(exception)")
        def to_raise_exception(context):

            context.memoize("exception_class", lambda _: RuntimeError)
            context.memoize("times", lambda _: 3)

            @context.shared_context
            def integration(context):
                @context.before
                def catch_callable_target_exceptions(self):
                    original_callable_target = self.callable_target

                    def _callable_target(*args, **kwargs):
                        with self.assertRaises(self.exception_class):
                            return original_callable_target(*args, **kwargs)

                    self.callable_target = _callable_target

                if has_original_callable:
                    context.nest_context("mock call arguments")
                context.nest_context("assertions")

            @context.sub_context
            def when_given_an_exception_class(context):
                @context.before
                def setup_mock(self):
                    self.mock_callable_dsl.to_raise(self.exception_class)

                @context.example
                def it_raises_an_instance_of_the_class(self):
                    with self.assertRaises(self.exception_class):
                        self.callable_target(*self.call_args, **self.call_kwargs)

                context.nest_context("integration")

            @context.sub_context
            def when_given_an_exception_instance(context):

                context.memoize("exception_message", lambda _: "test exception")
                context.memoize(
                    "exception",
                    lambda self: self.exception_class(self.exception_message),
                )

                @context.before
                def setup_mock(self):
                    self.mock_callable_dsl.to_raise(self.exception)

                @context.example
                def it_raises_the_exception_instance(self):
                    with self.assertRaises(self.exception_class) as cm:
                        self.callable_target(*self.call_args, **self.call_kwargs)
                    self.assertEqual(self.exception, cm.exception)

                context.nest_context("integration")

        @context.sub_context(".with_implementation(func)")
        def with_implementation_func(context):

            context.memoize("times", lambda _: 3)
            context.memoize("func_return", lambda _: "mocked response")

            @context.memoize
            def func(self):
                def _func(*args, **kwargs):
                    return self.func_return

                return _func

            @context.before
            def setup_mock(self):
                self.mock_callable_dsl.with_implementation(self.func)

            if has_original_callable:
                context.nest_context("mock call arguments")
            context.nest_context("assertions")

            @context.example
            def it_calls_new_implementation(self):
                self.assertEqual(
                    self.callable_target(*self.call_args, **self.call_kwargs),
                    self.func_return,
                )

        @context.sub_context(".with_wrapper(wrapper_func)")
        def with_wrapper_wrappr_func(context):

            context.memoize("func_return", lambda _: "mocked response")

            @context.memoize
            def wrapper_func(self):
                def _wrapper_func(original_function, *args, **kwargs):
                    self.assertEqual(original_function, self.original_callable)
                    return self.func_return

                return _wrapper_func

            if has_original_callable:

                context.memoize("times", lambda _: 3)

                @context.before
                def setup_mock(self):
                    self.mock_callable_dsl.with_wrapper(self.wrapper_func)

                context.nest_context("mock call arguments")
                context.nest_context("assertions")

                @context.example
                def it_calls_wrapper_function(self):
                    self.assertEqual(
                        self.callable_target(*self.call_args, **self.call_kwargs),
                        self.func_return,
                    )

            else:

                @context.example
                def it_fails_to_mock(self):
                    with self.assertRaisesWithMessage(
                        ValueError,
                        "Can not wrap original callable that does not exist.",
                    ):
                        self.mock_callable_dsl.with_wrapper(self.wrapper_func)

        @context.sub_context(".to_call_original()")
        def to_call_original(context):

            if has_original_callable:

                context.memoize("times", lambda _: 3)

                @context.before
                def setup_mock(self):
                    self.mock_callable_dsl.to_call_original()

                context.nest_context("mock call arguments")
                context.nest_context("assertions")

                @context.example
                def it_calls_original_implementation(self):
                    self.assertEqual(
                        self.callable_target(*self.call_args, **self.call_kwargs),
                        self.original_callable(*self.call_args, **self.call_kwargs),
                    )

            else:

                @context.example
                def it_fails_to_mock(self):
                    with self.assertRaisesWithMessage(
                        ValueError,
                        "Can not call original callable that does not exist.",
                    ):
                        self.mock_callable_dsl.to_call_original()

        if not callable_accepts_no_args:

            @context.sub_context
            def composition(context):
                """
                This context takes care of composition of multiple
                call/behavior/assertion combination, to ensure they play along well.
                """

                context.memoize(
                    "other_args", lambda self: ["other_arg" for arg in self.call_args]
                )
                context.memoize(
                    "other_kwargs",
                    lambda self: {
                        k: "other_value" for k, v in self.call_kwargs.items()
                    },
                )

                @context.example
                def newest_mock_has_precedence_over_older_mocks(self):
                    """
                    Mocks are designed to be composable, allowing us to declare
                    multiple behaviors for different calls. Those definitions stack up,
                    and when a call is made to the mock, they are searched from newest
                    to oldest, to find one that is able to be caled.
                    """
                    # First, mock all calls
                    mock_callable(self.target_arg, self.callable_arg).to_return_value(
                        "any args"
                    )
                    # Then we add some specific call behavior
                    mock_callable(self.target_arg, self.callable_arg).for_call(
                        *self.specific_call_args, **self.specific_call_kwargs
                    ).to_return_value("specific")
                    # The first behavior should still be there
                    self.assertEqual(
                        self.callable_target(*self.call_args, **self.call_kwargs),
                        "any args",
                    )
                    # as well as the specific case
                    self.assertEqual(
                        self.callable_target(
                            *self.specific_call_args, **self.specific_call_kwargs
                        ),
                        "specific",
                    )
                    # but if we add another "catch all" case
                    mock_callable(self.target_arg, self.callable_arg).to_return_value(
                        "new any args"
                    )
                    # it should take over any previous mock
                    self.assertEqual(
                        self.callable_target(*self.call_args, **self.call_kwargs),
                        "new any args",
                    )
                    self.assertEqual(
                        self.callable_target(
                            *self.specific_call_args, **self.specific_call_kwargs
                        ),
                        "new any args",
                    )

                @context.sub_context
                def multiple_assertions(context):
                    @context.before
                    def setup_mocks(self):
                        mock_callable(
                            self.target_arg, self.callable_arg
                        ).to_return_value("any args").and_assert_called_once()
                        mock_callable(self.target_arg, self.callable_arg).for_call(
                            *self.specific_call_args, **self.specific_call_kwargs
                        ).to_return_value("specific").and_assert_called_twice()

                    @context.example
                    def that_passes(self):
                        self.callable_target(*self.other_args, **self.other_kwargs)
                        self.callable_target(
                            *self.specific_call_args, **self.specific_call_kwargs
                        )
                        self.callable_target(
                            *self.specific_call_args, **self.specific_call_kwargs
                        )

                    @context.example
                    def that_fails(self):
                        # "Pass" this test when callable accepts no arguments
                        if (
                            self.specific_call_args == self.call_args
                            and self.specific_call_kwargs == self.call_kwargs
                        ):
                            raise RuntimeError("FIXME")
                            return
                        self.callable_target(*self.other_args, **self.other_kwargs)
                        self.callable_target(
                            *self.specific_call_args, **self.specific_call_kwargs
                        )
                        with self.assertRaises(AssertionError):
                            self.assert_all()

    ##
    ## Target types
    ##

    @context.sub_context
    def When_target_is_function_of_a_module(context):
        @context.before
        def before(self):
            self.original_callable = testslide._test_function
            self.real_target = testslide
            self.target_arg = "testslide"
            self.callable_arg = "_test_function"
            self.mock_callable_dsl = mock_callable(self.target_arg, self.callable_arg)
            self.callable_target = testslide._test_function

        context.merge_context("examples for target")

        @context.example
        def works_with_alternative_module_names(self):
            target = "os.path"
            target_module = os.path
            alternative_target = "testslide.cli.os.path"
            import testslide.cli

            alternative_target_module = testslide.cli.os.path
            original_function = os.path.exists

            self.mock_callable(target, "exists").for_call("found").to_return_value(True)
            self.mock_callable(alternative_target, "exists").for_call(
                "not_found"
            ).to_return_value(False)
            self.assertTrue(target_module.exists("found"))
            self.assertTrue(alternative_target_module.exists("found"))
            self.assertFalse(target_module.exists("not_found"))
            self.assertFalse(alternative_target_module.exists("not_found"))
            testslide.mock_callable.unpatch_all_callable_mocks()
            self.assertEqual(os.path.exists, original_function, "Unpatch did not work")

    @context.sub_context
    def When_target_is_a_builtin(context):
        context.memoize("call_args", lambda _: (0,))
        context.memoize("call_kwargs", lambda _: {})
        context.memoize("specific_call_args", lambda _: (0.000000001,))
        context.memoize("specific_call_kwargs", lambda _: {})

        @context.before
        def before(self):
            self.original_callable = time.sleep
            self.real_target = time
            self.target_arg = "time"
            self.callable_arg = "sleep"
            self.mock_callable_dsl = mock_callable(self.target_arg, self.callable_arg)
            self.callable_target = time.sleep

        context.merge_context("examples for target", validate_signature=False)

    @context.sub_context
    def When_target_is_instance_method_at_a_class(context):
        @context.example
        def it_is_not_allowed(self):
            with self.assertRaises(ValueError):
                mock_callable(Target, "instance_method")

    @context.sub_context
    def When_target_is_class_method_at_a_class(context):
        @context.before
        def before(self):
            self.original_callable = Target.class_method
            self.real_target = Target
            self.target_arg = Target
            self.callable_arg = "class_method"
            self.mock_callable_dsl = mock_callable(self.target_arg, self.callable_arg)
            self.callable_target = Target.class_method

        context.merge_context("examples for target")

    @context.sub_context
    def When_target_is_static_method_at_a_class(context):
        @context.before
        def before(self):
            self.original_callable = Target.static_method
            self.real_target = Target
            self.target_arg = Target
            self.callable_arg = "static_method"
            self.mock_callable_dsl = mock_callable(self.target_arg, self.callable_arg)
            self.callable_target = Target.static_method

        context.merge_context("examples for target")

    @context.shared_context
    def other_instances_are_not_mocked(context):
        @context.example
        def other_instances_are_not_mocked(self):
            mock_callable(self.target_arg, self.callable_arg).to_return_value(
                "mocked value"
            )
            self.assertEqual(
                self.callable_target(*self.call_args, **self.call_kwargs),
                "mocked value",
            )
            self.assertEqual(
                getattr(Target(), self.callable_arg)(
                    *self.call_args, **self.call_kwargs
                ),
                "original response",
            )

    @context.sub_context
    def When_target_is_instance_method_at_an_instance(context):

        context.memoize("callable_arg", lambda _: "instance_method")

        @context.before
        def before(self):
            target = Target()
            self.original_callable = target.instance_method
            self.real_target = target
            self.target_arg = target
            self.mock_callable_dsl = mock_callable(self.target_arg, self.callable_arg)
            self.callable_target = target.instance_method

        context.merge_context("examples for target")
        context.merge_context("other instances are not mocked")

    @context.sub_context
    def When_target_is_magic_instance_method_at_an_instance(context):

        context.memoize("call_args", lambda _: ())
        context.memoize("call_kwargs", lambda _: {})

        @context.shared_context
        def magic_method_tests(context):
            @context.before
            def before(self):
                self.original_callable = self.target.__str__
                self.real_target = self.target
                self.target_arg = self.target
                self.callable_arg = "__str__"
                self.mock_callable_dsl = mock_callable(
                    self.target_arg, self.callable_arg
                )
                self.callable_target = lambda: str(self.target)

            context.merge_context(
                "examples for target", callable_accepts_no_args=True, can_yield=False
            )

            @context.example
            def other_instances_are_not_mocked(self):
                mock_callable(self.target_arg, self.callable_arg).to_return_value(
                    "mocked value"
                )
                self.assertEqual(self.callable_target(), "mocked value")
                self.assertEqual(str(Target()), "original response")

        @context.sub_context
        def with_magic_method_defined_on_class(context):
            context.memoize("target", lambda self: ParentTarget())
            context.merge_context("magic method tests")

        @context.sub_context
        def with_magic_method_defined_on_parent_class(context):
            context.memoize("target", lambda self: Target())
            context.merge_context("magic method tests")

    @context.shared_context
    def class_is_not_mocked(context):
        @context.example
        def class_is_not_mocked(self):
            mock_callable(self.target_arg, self.callable_arg).to_return_value(
                "mocked value"
            )
            self.assertEqual(
                self.callable_target(*self.call_args, **self.call_kwargs),
                "mocked value",
            )
            self.assertEqual(
                getattr(Target, self.callable_arg)(*self.call_args, **self.call_kwargs),
                "original response",
            )

    @context.sub_context
    def When_target_is_class_method_at_an_instance(context):
        @context.before
        def before(self):
            target = Target()
            self.original_callable = target.class_method
            self.real_target = target
            self.target_arg = target
            self.callable_arg = "class_method"
            self.mock_callable_dsl = mock_callable(self.target_arg, self.callable_arg)
            self.callable_target = target.class_method

        context.merge_context("examples for target")
        context.merge_context("other instances are not mocked")
        context.merge_context("class is not mocked")

    @context.sub_context
    def When_target_is_static_method_at_an_instance(context):
        @context.before
        def before(self):
            target = Target()
            self.original_callable = target.static_method
            self.real_target = target
            self.target_arg = target
            self.callable_arg = "static_method"
            self.mock_callable_dsl = mock_callable(self.target_arg, self.callable_arg)
            self.callable_target = target.static_method

        context.merge_context("examples for target")
        context.merge_context("other instances are not mocked")
        context.merge_context("class is not mocked")

    @context.sub_context
    def When_target_is_a_StrictMock_instance(context):
        @context.shared_context
        def other_instances_are_not_mocked(context, runtime_attrs=[]):
            @context.example
            def other_instances_are_not_mocked(self):
                mock_callable(self.target_arg, self.callable_arg).to_return_value(
                    "mocked value"
                )
                self.assertEqual(
                    self.callable_target(*self.call_args, **self.call_kwargs),
                    "mocked value",
                )
                other_strict_mock = StrictMock(
                    template=Target, runtime_attrs=runtime_attrs
                )
                mock_callable(other_strict_mock, self.callable_arg).to_return_value(
                    "other mocked value"
                )
                self.assertEqual(
                    getattr(other_strict_mock, self.callable_arg)(
                        *self.call_args, **self.call_kwargs
                    ),
                    "other mocked value",
                )

        @context.sub_context
        def And_attribute_is_a_instance_method(context):

            context.memoize("callable_arg", lambda _: "instance_method")

            @context.before
            def before(self):
                target = StrictMock(template=Target)
                self.original_callable = None
                self.real_target = target
                self.target_arg = target
                self.mock_callable_dsl = mock_callable(
                    self.target_arg, self.callable_arg
                )
                self.callable_target = target.instance_method

            context.merge_context("examples for target", has_original_callable=False)

            context.merge_context("other instances are not mocked")

        @context.sub_context
        def And_attribute_is_a_magic_instance_method(context):

            context.memoize("call_args", lambda _: ())
            context.memoize("call_kwargs", lambda _: {})

            @context.before
            def before(self):
                target = StrictMock(template=Target)
                self.original_callable = None
                self.real_target = target
                self.target_arg = target
                self.callable_arg = "__str__"
                self.mock_callable_dsl = mock_callable(
                    self.target_arg, self.callable_arg
                )
                self.callable_target = lambda: str(target)

            context.merge_context(
                "examples for target",
                callable_accepts_no_args=True,
                has_original_callable=False,
                can_yield=False,
            )

            context.merge_context("other instances are not mocked")

        @context.sub_context
        def And_attribute_is_a_dynamic_instance_method(context):

            context.memoize("callable_arg", lambda _: "dynamic_instance_method")

            @context.before
            def before(self):
                target = StrictMock(
                    template=Target, runtime_attrs=["dynamic_instance_method"]
                )
                self.original_callable = None
                self.real_target = target
                self.target_arg = target
                self.mock_callable_dsl = mock_callable(
                    self.target_arg, self.callable_arg
                )
                self.callable_target = target.dynamic_instance_method

            context.merge_context("examples for target", has_original_callable=False)

            context.merge_context(
                "other instances are not mocked",
                runtime_attrs=["dynamic_instance_method"],
            )

        @context.sub_context
        def And_attribute_is_a_class_method(context):
            @context.before
            def before(self):
                target = StrictMock(template=Target)
                self.original_callable = None
                self.real_target = target
                self.target_arg = target
                self.callable_arg = "class_method"
                self.mock_callable_dsl = mock_callable(
                    self.target_arg, self.callable_arg
                )
                self.callable_target = target.class_method

            context.merge_context("examples for target", has_original_callable=False)
            context.merge_context("other instances are not mocked")
            context.merge_context("class is not mocked")

        @context.sub_context
        def And_attribute_is_a_static_method(context):
            @context.before
            def before(self):
                target = StrictMock(template=Target)
                self.original_callable = None
                self.real_target = target
                self.target_arg = target
                self.callable_arg = "static_method"
                self.mock_callable_dsl = mock_callable(
                    self.target_arg, self.callable_arg
                )
                self.callable_target = target.static_method

            context.merge_context("examples for target", has_original_callable=False)
            context.merge_context("other instances are not mocked")
            context.merge_context("class is not mocked")
