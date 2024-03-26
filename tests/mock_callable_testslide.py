# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import contextlib
import os

import testslide
from testslide.dsl import Skip, context, fcontext, xcontext  # noqa: F401
from testslide.lib import CoroutineValueError, TypeCheckError
from testslide.mock_callable import (
    UndefinedBehaviorForCall,
    UnexpectedCallArguments,
    UnexpectedCallReceived,
    mock_callable,
)
from testslide.strict_mock import StrictMock

from . import sample_module


async def coro_fun(*args):
    return 1


@context("mock_callable()")
def mock_callable_tests(context):
    ##
    ## Attributes
    ##

    context.memoize("assertions", lambda self: [])
    context.memoize("call_args", lambda self: ("first", "second"))
    context.memoize("call_kwargs", lambda self: {"kwarg1": "first", "kwarg2": "second"})
    context.memoize("type_validation", lambda self: True)

    @context.memoize
    def specific_call_args(self):
        return tuple("specific {}".format(arg) for arg in self.call_args)

    @context.memoize
    def specific_call_kwargs(self):
        return {k: "specific {}".format(v) for k, v in self.call_kwargs.items()}

    ##
    ## Functions
    ##

    @context.function
    def assert_all(self):
        try:
            for assertion in self.assertions:
                assertion()
        finally:
            del self.assertions[:]

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

    ##
    ## Hooks
    ##

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

    ##
    ## Examples
    ##
    @context.example
    def patching_private_functions_raises_valueerror(self):
        with self.assertRaises(ValueError):
            self.mock_callable(sample_module.TargetStr, "_privatefun")

    @context.example
    def patching_private_functions_with_allow_private(self):
        t = sample_module.TargetStr()
        self.mock_callable(t, "_privatefun", allow_private=True).to_return_value(
            "This fun is private"
        ).and_assert_called_once()
        t._privatefun()

    @context.example
    def patching_functions_in_slotted_class(self):
        t = sample_module.SomeClassWithSlots(attribute="value")
        self.mock_callable(t, "method").to_return_value(42).and_assert_called_once()
        self.assertEqual(t.method(), 42)

    @context.example
    def patching_functions_multiple_times_with_unhashable_class(self):
        t1 = sample_module.SomeUnhashableClass()
        t2 = sample_module.SomeUnhashableClass()
        t3 = sample_module.SomeUnhashableClass()
        self.mock_callable(t1, "method").to_return_value(0).and_assert_called_once()
        self.assertEqual(t1.method(), 0)
        self.mock_callable(t2, "method").to_return_value(1).and_assert_called_once()
        self.assertEqual(t2.method(), 1)
        self.mock_callable(t3, "method").to_return_value(2).and_assert_called_once()
        self.assertEqual(t3.method(), 2)

    ##
    ## Shared Contexts
    ##

    @context.shared_context
    def mock_configuration_examples(
        context, empty_args=False, has_original_callable=True, can_yield=True
    ):
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
                        "      {}={},\n".format(k, repr(self.call_kwargs[k]))
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
        def mock_call_arguments(context, has_return_value=True):
            @context.sub_context
            def mock_call(context):
                @context.sub_context
                def signature(context):
                    @context.example
                    def passes_with_valid_signature(self):
                        self.callable_target(*self.call_args, **self.call_kwargs)

                    @context.example
                    def raises_TypeError_for_mismatching_signature(self):
                        args = ("some", "invalid", "args", "list")
                        kwargs = {"invalid_kwarg": "invalid_value"}
                        with self.assertRaises(TypeError):
                            self.callable_target(*args, **kwargs)

                if not empty_args:

                    @context.sub_context
                    def type_validation(context):
                        @context.sub_context
                        def arguments(context):
                            @context.example
                            def raises_TypeCheckError_for_invalid_types(self):
                                bad_signature_args = (1234 for arg in self.call_args)
                                bad_signature_kargs = {
                                    k: 1234 for k, v in self.call_kwargs.items()
                                }
                                with self.assertRaises(TypeCheckError):
                                    self.callable_target(
                                        *bad_signature_args, **bad_signature_kargs
                                    )

                            @context.sub_context("with type_validation=False")
                            def with_type_validation_False(context):
                                context.memoize("type_validation", lambda self: False)

                                @context.example
                                def passes_with_invalid_argument_type(self):
                                    call_args = [1 for arg in self.call_args]
                                    call_kwargs = {
                                        key: 1 for key in self.call_kwargs.keys()
                                    }
                                    self.callable_target(*call_args, **call_kwargs)

                        if has_return_value:

                            @context.sub_context
                            def return_value(context):
                                @context.example
                                def passes_with_valid_type(self):
                                    self.callable_target(
                                        *self.call_args, **self.call_kwargs
                                    )

                                @context.sub_context
                                def with_invalid_return_type(context):
                                    context.memoize("value", lambda self: 1)
                                    context.memoize("values_list", lambda self: [1])

                                    @context.example
                                    def raises_TypeCheckError(self):
                                        with self.assertRaises(TypeCheckError):
                                            self.callable_target(
                                                *self.call_args, **self.call_kwargs
                                            )

            @context.sub_context(".for_call(*args, **kwargs)")
            def for_call_args_kwargs(context):
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

                if not empty_args:

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
                                        k, repr(self.specific_call_kwargs[k])
                                    )
                                    for k in sorted(self.specific_call_kwargs.keys())
                                )
                                + "    }\n",
                            ):
                                self.callable_target(
                                    *self.call_args, **self.call_kwargs
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

            @context.example
            def can_not_define_call_assertions(self):
                with self.assertRaisesRegex(
                    ValueError, "^You must first define a behavior.+"
                ):
                    self.mock_callable_dsl.and_assert_called_exactly(1)

            @context.example
            def mock_callable_can_not_assert_if_already_received_call(self):
                t = sample_module.SomeClass()
                mock = self.mock_callable(t, "method").to_return_value("value")
                t.method()
                with self.assertRaisesRegex(
                    ValueError,
                    "^No extra configuration is allowed after mock_callable.+self.mock_callable",
                ):
                    mock.and_assert_called_once()

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
                            "{}, {}: Expected not to be called!".format(
                                repr(self.real_target), repr(self.callable_arg)
                            ),
                        ):
                            self.callable_target(*self.call_args, **self.call_kwargs)

        @context.sub_context(".to_return(value)")
        def to_return_value(context):
            @context.memoize_before
            def value(self):
                # __str__ method is the only method returing `str`, while
                # all the other tested methods returns `List[str]`
                if self.callable_arg == "__str__":
                    return "mocked return"
                else:
                    return ["mocked return"]

            context.memoize("times", lambda self: 3)

            @context.before
            def setup_mock(self):
                self.mock_callable_dsl.to_return_value(self.value)

            if has_original_callable:
                context.merge_context("mock call arguments")
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

            @context.example
            def return_value_raises_with_coroutine(self):
                with self.assertRaises(CoroutineValueError):
                    self.mock_callable(
                        sample_module, "test_function", type_validation=False
                    ).to_return_value(coro_fun())

        @context.sub_context(".to_return_values(values_list)")
        def to_return_values_values_list(context):
            @context.memoize_before
            def values_list(self):
                # __str__ method is the only method returing `str`, while
                # all the other tested methods returns `List[str]`
                if self.callable_arg == "__str__":
                    return ["first", "second", "thrift"]
                else:
                    return [["first"], ["second"], ["thrift"]]

            context.memoize("value", lambda self: self.values_list[0])
            context.memoize("times", lambda self: len(self.values_list) - 1)

            @context.before
            def setup_mock(self):
                self.mock_callable_dsl.to_return_values(self.values_list)

            if has_original_callable:
                context.merge_context("mock call arguments")
            context.nest_context("assertions")

            @context.example
            def return_values_from_list_in_order(self):
                for value in self.values_list:
                    self.assertEqual(
                        self.callable_target(*self.call_args, **self.call_kwargs), value
                    )

            @context.example
            def return_values_raises_with_coroutine(self):
                with self.assertRaises(CoroutineValueError):
                    self.mock_callable(
                        sample_module, "test_function", type_validation=False
                    ).to_return_values([1, 2, coro_fun()])

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
                context.memoize(
                    "values_list", lambda self: [["first"], ["second"], ["third"]]
                )
                context.memoize("times", lambda self: len(self.values_list) - 1)

                @context.before
                def setup_mock(self):
                    self.mock_callable_dsl.to_yield_values(self.values_list)

                if has_original_callable:
                    context.merge_context("mock call arguments", has_return_value=False)
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

                @context.example
                def yield_values_raises_with_coroutine(self):
                    with self.assertRaises(CoroutineValueError):
                        self.mock_callable(
                            sample_module, "test_function", type_validation=False
                        ).to_yield_values([1, 2, coro_fun()])

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
            context.memoize("exception_class", lambda self: RuntimeError)
            context.memoize("times", lambda self: 3)

            @context.shared_context
            def integration(context):
                @context.memoize_before
                def _original_target(self):
                    return getattr(self.real_target, self.callable_arg)

                @context.memoize_before
                def callable_target(self):
                    original_callable_target = self._original_target

                    def _callable_target(*args, **kwargs):
                        with self.assertRaises(self.exception_class):
                            return original_callable_target(*args, **kwargs)

                    return _callable_target

                if has_original_callable:
                    context.merge_context("mock call arguments", has_return_value=False)
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
                context.memoize("exception_message", lambda self: "test exception")
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
            @context.memoize_before
            def value(self):
                # __str__ method is the only method returing `str`, while
                # all the other tested methods returns `List[str]`
                if self.callable_arg == "__str__":
                    return "mocked return"
                else:
                    return ["mocked return"]

            context.memoize("times", lambda self: 3)
            context.memoize("func_return", lambda self: self.value)

            @context.memoize
            def func(self):
                def _func(*args, **kwargs):
                    return self.func_return

                return _func

            @context.before
            def setup_mock(self):
                self.mock_callable_dsl.with_implementation(self.func)

            if has_original_callable:
                context.merge_context("mock call arguments")
            context.nest_context("assertions")

            @context.example
            def it_calls_new_implementation(self):
                self.assertEqual(
                    self.callable_target(*self.call_args, **self.call_kwargs),
                    self.func_return,
                )

            @context.example
            def with_implementation_raises_with_coroutine(self):
                self.mock_callable(
                    sample_module, "test_function", type_validation=False
                ).with_implementation(coro_fun)
                with self.assertRaises(CoroutineValueError):
                    sample_module.test_function("a", "")

        @context.sub_context(".with_wrapper(wrapper_func)")
        def with_wrapper_wrappr_func(context):
            @context.memoize_before
            def value(self):
                # __str__ method is the only method returing `str`, while
                # all the other tested methods returns `List[str]`
                if self.callable_arg == "__str__":
                    return "mocked return"
                else:
                    return ["mocked return"]

            context.memoize("func_return", lambda self: self.value)

            @context.memoize
            def wrapper_func(self):
                def _wrapper_func(original_function, *args, **kwargs):
                    self.assertEqual(original_function, self.original_callable)
                    return self.func_return

                return _wrapper_func

            if has_original_callable:
                context.memoize("times", lambda self: 3)

                @context.before
                def setup_mock(self):
                    self.mock_callable_dsl.with_wrapper(self.wrapper_func)

                context.merge_context("mock call arguments")
                context.nest_context("assertions")

                @context.example
                def it_calls_wrapper_function(self):
                    self.assertEqual(
                        self.callable_target(*self.call_args, **self.call_kwargs),
                        self.func_return,
                    )

                @context.example
                def with_wrapper_raises_with_coroutine(self):
                    async def _wrapper_coro_func(original_function, *args, **kwargs):
                        self.assertEqual(original_function, self.original_callable)
                        return self.func_return

                    self.mock_callable(
                        sample_module, "test_function", type_validation=False
                    ).with_wrapper(_wrapper_coro_func)

                    with self.assertRaises(CoroutineValueError):
                        sample_module.test_function("a", "")

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
                context.memoize("times", lambda self: 3)

                @context.before
                def setup_mock(self):
                    self.mock_callable_dsl.to_call_original()

                context.merge_context("mock call arguments", has_return_value=False)
                context.nest_context("assertions")

                @context.example
                def it_calls_original_implementation(self):
                    self.assertEqual(
                        self.callable_target(*self.call_args, **self.call_kwargs),
                        self.original_callable(*self.call_args, **self.call_kwargs),
                    )

                if not empty_args:

                    @context.sub_context("with type_validation=False")
                    def with_type_validation_False(context):
                        context.memoize("type_validation", lambda self: False)

                        @context.example
                        def it_doest_not_type_validate(self):
                            call_args = [1 for arg in self.call_args]
                            call_kwargs = {key: 1 for key in self.call_kwargs.keys()}
                            mock_callable(
                                self.target_arg,
                                self.callable_arg,
                                type_validation=self.type_validation,
                            ).for_call(*call_args, **call_kwargs).to_return_value(None)
                            self.callable_target(*call_args, **call_kwargs)

            else:

                @context.example
                def it_fails_to_mock(self):
                    with self.assertRaisesWithMessage(
                        ValueError,
                        "Can not call original callable that does not exist.",
                    ):
                        self.mock_callable_dsl.to_call_original()

        if not empty_args:

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
                        ["any args"]
                    )
                    # Then we add some specific call behavior
                    mock_callable(self.target_arg, self.callable_arg).for_call(
                        *self.specific_call_args, **self.specific_call_kwargs
                    ).to_return_value(["specific"])
                    # The first behavior should still be there
                    self.assertEqual(
                        self.callable_target(*self.call_args, **self.call_kwargs),
                        ["any args"],
                    )
                    # as well as the specific case
                    self.assertEqual(
                        self.callable_target(
                            *self.specific_call_args, **self.specific_call_kwargs
                        ),
                        ["specific"],
                    )
                    # but if we add another "catch all" case
                    mock_callable(self.target_arg, self.callable_arg).to_return_value(
                        ["new any args"]
                    )
                    # it should take over any previous mock
                    self.assertEqual(
                        self.callable_target(*self.call_args, **self.call_kwargs),
                        ["new any args"],
                    )
                    self.assertEqual(
                        self.callable_target(
                            *self.specific_call_args, **self.specific_call_kwargs
                        ),
                        ["new any args"],
                    )

                @context.sub_context
                def multiple_assertions(context):
                    @context.before
                    def setup_mocks(self):
                        mock_callable(
                            self.target_arg, self.callable_arg
                        ).to_return_value(["any args"]).and_assert_called_once()
                        mock_callable(self.target_arg, self.callable_arg).for_call(
                            *self.specific_call_args, **self.specific_call_kwargs
                        ).to_return_value(["specific"]).and_assert_called_twice()

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

    @context.shared_context
    def class_is_not_mocked(context):
        @context.example
        def class_is_not_mocked(self):
            mock_callable(self.target_arg, self.callable_arg).to_return_value(
                ["mocked value"]
            )
            self.assertEqual(
                self.callable_target(*self.call_args, **self.call_kwargs),
                ["mocked value"],
            )
            self.assertEqual(
                getattr(sample_module.Target, self.callable_arg)(
                    *self.call_args, **self.call_kwargs
                ),
                ["original response"],
            )

    @context.shared_context
    def can_not_mock_async_callable(context):
        @context.example
        def can_not_mock(self):
            with self.assertRaisesRegex(
                ValueError,
                getattr(
                    self,
                    "exception_regex_message",
                    r"mock_callable\(\) can not be used with coroutine functions\.",
                ),
            ):
                mock_callable(self.target_arg, self.callable_arg)

    @context.shared_context
    def async_methods_examples(context, not_in_class_instance_method=False):
        @context.sub_context
        def and_callable_is_an_async_instance_method(context):
            context.memoize("callable_arg", lambda self: "async_instance_method")

            if not_in_class_instance_method:

                @context.memoize
                def exception_regex_message(self):
                    return "Patching an instance method at the class is not supported"

            context.merge_context("can not mock async callable")

        @context.sub_context
        def and_callable_is_an_async_class_method(context):
            context.memoize("callable_arg", lambda self: "async_class_method")

            context.merge_context("can not mock async callable")

        @context.sub_context
        def and_callable_is_an_async_static_method(context):
            context.memoize("callable_arg", lambda self: "async_static_method")

            context.merge_context("can not mock async callable")

        @context.sub_context
        def and_callable_is_an_async_magic_method(context):
            context.memoize("callable_arg", lambda self: "__aiter__")

            if not_in_class_instance_method:

                @context.memoize
                def exception_regex_message(self):
                    return "Patching an instance method at the class is not supported"

            context.merge_context("can not mock async callable")

    ##
    ## Contexts
    ##

    @context.sub_context
    def call_order_assertion(context):
        @context.memoize
        def target1(self):
            return sample_module.CallOrderTarget("target1")

        @context.memoize
        def target2(self):
            return sample_module.CallOrderTarget("target2")

        @context.before
        def define_assertions(self):
            self.mock_callable(self.target1, "f1").for_call("step 1").to_return_value(
                "step 1 return"
            ).and_assert_called_ordered()
            self.mock_callable(self.target1, "f2").to_return_value(
                "step 2 return"
            ).and_assert_called_ordered()
            self.mock_callable(self.target2, "f1").for_call("step 3").to_return_value(
                "step 3 return"
            ).and_assert_called_ordered()

        @context.example
        def it_passes_with_ordered_calls(self):
            self.assertEqual(self.target1.f1("step 1"), "step 1 return")
            self.assertEqual(self.target1.f2("step 2"), "step 2 return")
            self.assertEqual(self.target2.f1("step 3"), "step 3 return")
            self.assert_all()

        @context.example
        def it_fails_with_unordered_calls(self):
            self.assertEqual(self.target1.f2("step 2"), "step 2 return")
            self.assertEqual(self.target2.f1("step 3"), "step 3 return")
            self.assertEqual(self.target1.f1("step 1"), "step 1 return")
            with self.assertRaisesWithMessage(
                AssertionError,
                "calls did not match assertion.\n"
                + "\n"
                + "These calls were expected to have happened in order:\n"
                + "\n"
                + "  target1, {} with arguments:\n".format(repr("f1"))
                + "    {}\n".format(repr(("step 1",)))
                + "  target1, {} with any arguments\n".format(repr("f2"))
                + "  target2, {} with arguments:\n".format(repr("f1"))
                + "    {}\n".format(repr(("step 3",)))
                + "\n"
                + "but these calls were made:\n"
                + "\n"
                + "  target1, {} with any arguments\n".format(repr("f2"))
                + "  target2, {} with arguments:\n".format(repr("f1"))
                + "    {}\n".format(repr(("step 3",)))
                + "  target1, {} with arguments:\n".format(repr("f1"))
                + "    {}".format(repr(("step 1",))),
            ):
                self.assert_all()

        @context.example
        def it_fails_with_partial_calls(self):
            self.assertEqual(self.target1.f2("step 2"), "step 2 return")
            self.assertEqual(self.target2.f1("step 3"), "step 3 return")
            with self.assertRaisesWithMessage(
                AssertionError,
                "calls did not match assertion.\n"
                + "\n"
                + "These calls were expected to have happened in order:\n"
                + "\n"
                + "  target1, {} with arguments:\n".format(repr("f1"))
                + "    {}\n".format(repr(("step 1",)))
                + "  target1, {} with any arguments\n".format(repr("f2"))
                + "  target2, {} with arguments:\n".format(repr("f1"))
                + "    {}\n".format(repr(("step 3",)))
                + "\n"
                + "but these calls were made:\n"
                + "\n"
                + "  target1, {} with any arguments\n".format(repr("f2"))
                + "  target2, {} with arguments:\n".format(repr("f1"))
                + "    {}".format(repr(("step 3",))),
            ):
                self.assert_all()

        @context.example
        def other_mocks_do_not_interfere(self):
            self.mock_callable(self.target1, "f1").for_call(
                "unrelated 1"
            ).to_return_value("unrelated 1 return").and_assert_called_once()

            self.assertEqual(self.target1.f1("unrelated 1"), "unrelated 1 return")

            self.mock_callable(self.target2, "f1").for_call(
                "unrelated 3"
            ).to_return_value("unrelated 3 return")

            self.assertEqual(self.target1.f1("step 1"), "step 1 return")
            self.assertEqual(self.target1.f2("step 2"), "step 2 return")
            self.assertEqual(self.target2.f1("step 3"), "step 3 return")
            self.assert_all()

    @context.sub_context
    def when_target_is_a_module(context):
        context.memoize("target_arg", lambda self: "tests.sample_module")
        context.memoize("real_target", lambda self: sample_module)

        @context.example
        def works_with_alternative_module_names(self):
            target = "os.path"
            target_module = os.path
            alternative_target = "testslide.cli.os.path"
            import testslide.cli

            alternative_target_module = testslide.cli.os.path
            original_function = os.path.exists

            # this is needed because `inspect.getframeinfo` calls `os.exist` under the hood
            self.mock_callable(target, "exists").to_call_original()
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
        def and_callable_is_a_function(context):
            context.memoize("callable_arg", lambda self: "test_function")

            @context.memoize_before
            def original_callable(self):
                return getattr(self.real_target, self.callable_arg)

            @context.memoize_before
            def mock_callable_dsl(self):
                return mock_callable(
                    self.target_arg,
                    self.callable_arg,
                    type_validation=self.type_validation,
                )

            @context.memoize_before
            def callable_target(self):
                return getattr(self.real_target, self.callable_arg)

            context.merge_context("mock configuration examples")

        @context.sub_context
        def and_callable_is_an_async_function(context):
            context.memoize("callable_arg", lambda self: "async_test_function")

            context.merge_context("can not mock async callable")

    @context.sub_context
    def when_target_is_a_class(context):
        @context.memoize_before
        def real_target(self):
            return sample_module.Target

        @context.memoize_before
        def target_arg(self):
            return sample_module.Target

        context.merge_context(
            "async methods examples", not_in_class_instance_method=True
        )

        @context.sub_context
        def and_callable_is_an_instance_method(context):
            @context.example
            def it_is_not_allowed(self):
                with self.assertRaises(ValueError):
                    mock_callable(sample_module.Target, "instance_method")

        @context.sub_context
        def and_callable_is_a_class_method(context):
            @context.memoize_before
            def original_callable(self):
                return sample_module.Target.class_method

            context.memoize("callable_arg", lambda self: "class_method")

            @context.memoize_before
            def mock_callable_dsl(self):
                return mock_callable(
                    self.target_arg,
                    self.callable_arg,
                    type_validation=self.type_validation,
                )

            @context.memoize_before
            def callable_target(self):
                return sample_module.Target.class_method

            @context.memoize_before
            def _original_target(self):
                return sample_module.Target.class_method

            context.merge_context("mock configuration examples")

        @context.sub_context
        def and_callable_is_a_static_method(context):
            @context.memoize_before
            def original_callable(self):
                return sample_module.Target.static_method

            context.memoize("callable_arg", lambda self: "static_method")

            @context.memoize_before
            def mock_callable_dsl(self):
                return mock_callable(
                    self.target_arg,
                    self.callable_arg,
                    type_validation=self.type_validation,
                )

            @context.memoize_before
            def callable_target(self):
                return sample_module.Target.static_method

            @context.memoize_before
            def _original_target(self):
                return sample_module.Target.static_method

            context.merge_context("mock configuration examples")

        @context.sub_context
        def and_callable_is_a_magic_method(context):
            @context.example
            def it_is_not_allowed(self):
                with self.assertRaises(ValueError):
                    mock_callable(sample_module.Target, "__str__")

    @context.sub_context
    def an_instance(context):
        @context.memoize_before
        def target(self):
            return sample_module.Target()

        @context.memoize_before
        def real_target(self):
            return self.target

        @context.memoize_before
        def target_arg(self):
            return self.target

        context.merge_context("async methods examples")

        @context.shared_context
        def other_instances_are_not_mocked(context):
            @context.example
            def other_instances_are_not_mocked(self):
                mock_callable(self.target_arg, self.callable_arg).to_return_value(
                    ["mocked value"]
                )
                self.assertEqual(
                    self.callable_target(*self.call_args, **self.call_kwargs),
                    ["mocked value"],
                )
                self.assertEqual(
                    getattr(sample_module.Target(), self.callable_arg)(
                        *self.call_args, **self.call_kwargs
                    ),
                    ["original response"],
                )

        @context.sub_context
        def and_callable_is_an_instance_method(context):
            context.memoize("callable_arg", lambda self: "instance_method")

            @context.memoize_before
            def original_callable(self):
                return self.real_target.instance_method

            @context.memoize_before
            def mock_callable_dsl(self):
                return mock_callable(
                    self.target_arg,
                    self.callable_arg,
                    type_validation=self.type_validation,
                )

            @context.memoize_before
            def callable_target(self):
                return self.real_target.instance_method

            @context.memoize_before
            def _original_target(self):
                return self.real_target.instance_method

            context.merge_context("mock configuration examples")
            context.merge_context("other instances are not mocked")

        @context.sub_context
        def and_callable_is_a_class_method(context):
            @context.memoize_before
            def original_callable(self):
                return self.real_target.class_method

            context.memoize("callable_arg", lambda self: "class_method")

            @context.memoize_before
            def mock_callable_dsl(self):
                return mock_callable(
                    self.target_arg,
                    self.callable_arg,
                    type_validation=self.type_validation,
                )

            @context.memoize_before
            def callable_target(self):
                return self.real_target.class_method

            @context.memoize_before
            def _original_target(self):
                return self.real_target.class_method

            context.merge_context("mock configuration examples")
            context.merge_context("other instances are not mocked")
            context.merge_context("class is not mocked")

        @context.sub_context
        def and_callable_is_a_static_method(context):
            @context.memoize_before
            def original_callable(self):
                return self.real_target.static_method

            context.memoize("callable_arg", lambda self: "static_method")

            @context.memoize_before
            def mock_callable_dsl(self):
                return mock_callable(
                    self.target_arg,
                    self.callable_arg,
                    type_validation=self.type_validation,
                )

            @context.memoize_before
            def callable_target(self):
                return self.real_target.static_method

            @context.memoize_before
            def _original_target(self):
                return self.real_target.static_method

            context.merge_context("mock configuration examples")
            context.merge_context("other instances are not mocked")
            context.merge_context("class is not mocked")

        @context.sub_context
        def and_callable_is_a_magic_method(context):
            context.memoize("call_args", lambda self: ())
            context.memoize("call_kwargs", lambda self: {})

            @context.shared_context
            def magic_method_tests(context):
                @context.memoize_before
                def original_callable(self):
                    return self.target.__str__

                @context.memoize_before
                def real_target(self):
                    return self.target

                @context.memoize_before
                def target_arg(self):
                    return self.target

                context.memoize("callable_arg", lambda self: "__str__")

                @context.memoize_before
                def mock_callable_dsl(self):
                    return mock_callable(
                        self.target_arg,
                        self.callable_arg,
                        type_validation=self.type_validation,
                    )

                @context.memoize_before
                def callable_target(self):
                    return lambda: str(self.target)

                @context.memoize_before
                def _original_target(self):
                    return lambda: str(self.target)

                context.merge_context(
                    "mock configuration examples", empty_args=True, can_yield=False
                )

                @context.example
                def other_instances_are_not_mocked(self):
                    @context.memoize_before
                    def value(self):
                        # __str__ method is the only method returing `str`, while
                        # all the other tested methods returns `List[str]`
                        if self.callable_arg == "__str__":
                            return "mocked value"
                        else:
                            return ["mocked value"]

                    mock_callable(self.target_arg, self.callable_arg).to_return_value(
                        self.value,
                    )
                    self.assertEqual(self.callable_target(), self.value)
                    self.assertEqual(str(sample_module.Target()), "original response")

            @context.sub_context
            def with_magic_method_defined_on_class(context):
                context.memoize("target", lambda self: sample_module.ParentTarget())
                context.merge_context("magic method tests")

            @context.sub_context
            def with_magic_method_defined_on_parent_class(context):
                context.memoize("target", lambda self: sample_module.Target())
                context.merge_context("magic method tests")

    @context.sub_context
    def when_target_is_a_StrictMock(context):
        @context.memoize_before
        def target(self):
            return StrictMock(template=sample_module.Target)

        @context.memoize_before
        def real_target(self):
            return self.target

        @context.memoize_before
        def target_arg(self):
            return self.target

        @context.before
        def before(self):
            self.original_callable = None

        context.merge_context("async methods examples")

        @context.shared_context
        def other_instances_are_not_mocked(context, runtime_attrs=[]):
            @context.memoize_before
            def build_value(self):
                # __str__ method is the only method returing `str`, while
                # all the other tested methods returns `List[str]`
                if self.callable_arg == "__str__":
                    return lambda value: value
                else:
                    return lambda value: [value]

            @context.example
            def other_instances_are_not_mocked(self):
                mock_callable(self.target_arg, self.callable_arg).to_return_value(
                    self.build_value("mocked value"),
                )
                self.assertEqual(
                    self.callable_target(*self.call_args, **self.call_kwargs),
                    self.build_value("mocked value"),
                )
                other_strict_mock = StrictMock(
                    template=sample_module.Target, runtime_attrs=runtime_attrs
                )
                mock_callable(other_strict_mock, self.callable_arg).to_return_value(
                    self.build_value("other mocked value"),
                )
                self.assertEqual(
                    getattr(other_strict_mock, self.callable_arg)(
                        *self.call_args, **self.call_kwargs
                    ),
                    self.build_value("other mocked value"),
                )

        @context.sub_context
        def and_callable_is_an_instance_method(context):
            context.memoize("callable_arg", lambda self: "instance_method")

            @context.sub_context
            def that_is_statically_defined_at_the_class(context):
                @context.memoize_before
                def mock_callable_dsl(self):
                    return mock_callable(self.target_arg, self.callable_arg)

                @context.memoize_before
                def callable_target(self):
                    return self.real_target.instance_method

                @context.memoize_before
                def _original_target(self):
                    return self.real_target.instance_method

                context.merge_context(
                    "mock configuration examples", has_original_callable=False
                )

                context.merge_context("other instances are not mocked")

            @context.sub_context
            def that_is_dynamically_defined_by_the_instance(context):
                context.memoize("callable_arg", lambda self: "dynamic_instance_method")

                @context.memoize_before
                def target(self):
                    return StrictMock(
                        template=sample_module.Target,
                        runtime_attrs=["dynamic_instance_method"],
                    )

                @context.memoize_before
                def real_target(self):
                    return self.target

                @context.memoize_before
                def target_arg(self):
                    return self.target

                @context.before
                def before(self):
                    self.original_callable = None

                @context.memoize_before
                def mock_callable_dsl(self):
                    return mock_callable(self.target_arg, self.callable_arg)

                @context.memoize_before
                def callable_target(self):
                    return self.real_target.dynamic_instance_method

                @context.memoize_before
                def _original_target(self):
                    return self.real_target.dynamic_instance_method

                context.merge_context(
                    "mock configuration examples", has_original_callable=False
                )

                context.merge_context(
                    "other instances are not mocked",
                    runtime_attrs=["dynamic_instance_method"],
                )

        @context.sub_context
        def and_callable_is_a_class_method(context):
            context.memoize("callable_arg", lambda self: "class_method")

            @context.memoize_before
            def mock_callable_dsl(self):
                return mock_callable(self.target_arg, self.callable_arg)

            @context.memoize_before
            def callable_target(self):
                return self.real_target.class_method

            @context.memoize_before
            def _original_target(self):
                return self.real_target.class_method

            context.merge_context(
                "mock configuration examples", has_original_callable=False
            )
            context.merge_context("other instances are not mocked")
            context.merge_context("class is not mocked")

        @context.sub_context
        def and_callable_is_a_static_method(context):
            context.memoize("callable_arg", lambda self: "static_method")

            @context.memoize_before
            def mock_callable_dsl(self):
                return mock_callable(self.target_arg, self.callable_arg)

            @context.memoize_before
            def callable_target(self):
                return self.real_target.static_method

            @context.memoize_before
            def _original_target(self):
                return self.real_target.static_method

            context.merge_context(
                "mock configuration examples", has_original_callable=False
            )
            context.merge_context("other instances are not mocked")
            context.merge_context("class is not mocked")

        @context.sub_context
        def and_callable_is_a_magic_method(context):
            context.memoize("call_args", lambda self: ())
            context.memoize("call_kwargs", lambda self: {})
            context.memoize("callable_arg", lambda self: "__str__")

            @context.memoize_before
            def mock_callable_dsl(self):
                return mock_callable(self.target_arg, self.callable_arg)

            @context.memoize_before
            def callable_target(self):
                return lambda: str(self.real_target)

            @context.memoize_before
            def _original_target(self):
                return lambda: str(self.real_target)

            context.merge_context(
                "mock configuration examples",
                empty_args=True,
                has_original_callable=False,
                can_yield=False,
            )
            context.merge_context("other instances are not mocked")

    @context.sub_context
    def mock_sync_async_callable_type_check_errors(context):
        @context.shared_context
        def run_context(context, target):
            @context.example
            def mock_callable_to_return_value(self):
                self.mock_callable(target, "instance_method").to_return_value(
                    1
                ).and_assert_called()

                # instance_method is annotated to return a string and here we would retrieve 1
                with self.assertRaises(TypeCheckError):
                    target.instance_method(
                        arg1="arg1", arg2="arg2", kwarg1="kwarg1", kwarg2="kwarg2"
                    )

            @context.example
            def mock_callable_to_return_values(self):
                self.mock_callable(target, "instance_method").to_return_values(
                    [1, 2, ["ok"]]
                ).and_assert_called()

                # instance_method should return `List[str]` while 1 is `int`
                with self.assertRaises(TypeCheckError):
                    target.instance_method(
                        arg1="arg1", arg2="arg2", kwarg1="kwarg1", kwarg2="kwarg2"
                    )

                # instance_method should return `List[str]` while 2 is `int`
                with self.assertRaises(TypeCheckError):
                    target.instance_method(
                        arg1="arg1", arg2="arg2", kwarg1="kwarg1", kwarg2="kwarg2"
                    )

                # instance_method should return `List[str]` and ["ok"] is correct
                target.instance_method(
                    arg1="arg1", arg2="arg2", kwarg1="kwarg1", kwarg2="kwarg2"
                )

            @context.example
            def mock_callable_with_implementation(self):
                self.mock_callable(target, "instance_method").with_implementation(
                    lambda arg1, **kwargs: 1 if arg1 == "give_me_an_int" else [arg1]
                ).and_assert_called()

                # instance_method should return `List[str]` while 1 is `int`
                with self.assertRaises(TypeCheckError):
                    target.instance_method(
                        arg1="give_me_an_int",
                        arg2="arg2",
                        kwarg1="kwarg1",
                        kwarg2="kwarg2",
                    )

                # instance_method should return `List[str]` and ["ok"] is correct
                target.instance_method(
                    arg1="arg1", arg2="arg2", kwarg1="kwarg1", kwarg2="kwarg2"
                )

            @context.example
            def mock_async_callable_to_return_value(self):
                self.mock_async_callable(
                    target, "async_instance_method"
                ).to_return_value(1).and_assert_called()

                # instance_method is annotated to return a string and here we would retrieve 1
                with self.assertRaises(TypeCheckError):
                    self.async_run_with_health_checks(
                        target.async_instance_method(
                            arg1="arg1", arg2="arg2", kwarg1="kwarg1", kwarg2="kwarg2"
                        )
                    )

            @context.example
            def mock_async_callable_to_return_values(self):
                self.mock_async_callable(
                    target, "async_instance_method"
                ).to_return_values([1, 2, ["ok"]]).and_assert_called()

                # instance_method is annotated to return a string and here we would retrieve 1
                with self.assertRaises(TypeCheckError):
                    self.async_run_with_health_checks(
                        target.async_instance_method(
                            arg1="arg1", arg2="arg2", kwarg1="kwarg1", kwarg2="kwarg2"
                        )
                    )

                # instance_method should return `List[str]` while 2 is `int`
                with self.assertRaises(TypeCheckError):
                    self.async_run_with_health_checks(
                        target.async_instance_method("arg1", "arg2")
                    )

                self.async_run_with_health_checks(
                    target.async_instance_method("arg1", "arg2")
                )

            @context.example
            def mock_async_callable_with_implementation(self):
                async def impl(arg1: str, arg2: str, **kwargs):
                    return 1 if arg1 == "give_me_an_int" else [arg1]

                self.mock_async_callable(
                    target, "async_instance_method"
                ).with_implementation(impl).and_assert_called()

                # instance_method is annotated to return a string and here we would retrieve an integer
                with self.assertRaises(TypeCheckError):
                    self.async_run_with_health_checks(
                        target.async_instance_method("give_me_an_int", "arg2")
                    )

                self.async_run_with_health_checks(
                    target.async_instance_method("arg1", "arg2")
                )

        @context.sub_context
        def using_concrete_instance(context):
            context.merge_context("run context", target=sample_module.Target())

        @context.sub_context
        def using_strict_mock(context):
            context.merge_context(
                "run context", target=StrictMock(sample_module.ParentTarget)
            )
