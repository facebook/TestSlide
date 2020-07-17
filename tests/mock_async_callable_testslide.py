# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import testslide
from testslide.dsl import context, xcontext, fcontext, Skip  # noqa: F401

from testslide.mock_callable import (
    mock_async_callable,
    NotACoroutine,
    UndefinedBehaviorForCall,
    UnexpectedCallArguments,
)
import contextlib
from testslide.strict_mock import StrictMock
from . import sample_module
from testslide.lib import TypeCheckError


@context("mock_async_callable()")
def mock_async_callable_tests(context):

    ##
    ## Attributes
    ##

    @context.memoize_before
    async def assertions(self):
        return []

    @context.memoize_before
    async def value(self):
        return "mocked value"

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
    async def register_assertions(self):
        def register_assertion(assertion):
            self.assertions.append(assertion)

        testslide.mock_callable.register_assertion = register_assertion

    @context.after
    async def cleanup_patches(self):
        # Unpatch before assertions, to make sure it is done if assertion fails.
        testslide.mock_callable.unpatch_all_callable_mocks()
        for assertion in self.assertions:
            assertion()

    ##
    ## Shared Contexts
    ##

    @context.shared_context
    def mock_async_callable_with_sync_exapmles(context, can_mock_with_flag=True):
        @context.example
        async def can_not_mock(self):
            with self.assertRaisesRegex(
                ValueError,
                getattr(
                    self,
                    "exception_regex_message",
                    "mock_async_callable\(\) can not be used with non coroutine functions\.",
                ),
            ):
                mock_async_callable(self.target_arg, self.callable_arg)

        if can_mock_with_flag:

            @context.example
            async def can_mock_with_flag(self):
                mock_async_callable(
                    self.target_arg, self.callable_arg, callable_returns_coroutine=True
                )

    @context.shared_context
    def mock_configuration_examples(
        context, empty_args=False, can_yield=False, has_original_callable=True
    ):
        @context.shared_context
        def return_value_type(context):
            if not empty_args and has_original_callable:

                @context.example
                async def passes_with_valid_type(self):
                    await self.callable_target(*self.call_args, **self.call_kwargs)

                @context.sub_context
                def with_invalid_return_type(context):
                    @context.memoize_before
                    async def value(self):
                        return 1

                    @context.example
                    async def raises_TypeCheckError(self):
                        with self.assertRaises(TypeCheckError):
                            await self.callable_target(
                                *self.call_args, **self.call_kwargs
                            )

        @context.example
        async def default_behavior(self):
            mock_async_callable(self.target_arg, self.callable_arg)
            with self.assertRaises(UndefinedBehaviorForCall):
                await self.callable_target(*self.call_args, **self.call_kwargs)

        @context.example(".for_call()")
        async def for_call(self):
            mock_args = tuple(f"mock {str(arg)}" for arg in self.call_args)
            mock_kwargs = {k: f"mock {str(v)}" for k, v in self.call_kwargs.items()}
            mock_async_callable(self.target_arg, self.callable_arg).for_call(
                *mock_args, **mock_kwargs
            ).to_return_value("mock")
            self.assertEqual(
                await self.callable_target(*mock_args, **mock_kwargs), "mock"
            )
            if mock_args or mock_kwargs:
                with self.assertRaises(UnexpectedCallArguments):
                    await self.callable_target(*self.call_args, **self.call_kwargs)

        @context.sub_context(".to_return_value(value)")
        def to_return_value_value(context):
            @context.before
            async def before(self):
                mock_async_callable(self.target_arg, self.callable_arg).to_return_value(
                    self.value
                )
                self.callable_target = getattr(self.real_target, self.callable_arg)

            @context.example
            async def it_returns_value(self):
                self.assertEqual(
                    await self.callable_target(*self.call_args, **self.call_kwargs),
                    self.value,
                )

            context.nest_context("return value type")

        @context.sub_context(".to_return_values(value_list)")
        def to_return_values(context):
            @context.before
            async def before(self):
                mock_async_callable(
                    self.target_arg, self.callable_arg
                ).to_return_values([self.value, "mock2"])
                self.callable_target = getattr(self.real_target, self.callable_arg)

            @context.example
            async def it_returns_values(self):
                self.assertEqual(
                    await self.callable_target(*self.call_args, **self.call_kwargs),
                    self.value,
                )
                self.assertEqual(
                    await self.callable_target(*self.call_args, **self.call_kwargs),
                    "mock2",
                )
                with self.assertRaisesRegex(
                    UndefinedBehaviorForCall, "No more values to return!"
                ):
                    await self.callable_target(*self.call_args, **self.call_kwargs)

            context.nest_context("return value type")

        @context.example(".to_raise(exception)")
        async def to_raise(self):
            mock_async_callable(self.target_arg, self.callable_arg).to_raise(
                RuntimeError("mock")
            )
            with self.assertRaisesWithMessage(RuntimeError, "mock"):
                await self.callable_target(*self.call_args, **self.call_kwargs)

        @context.sub_context(".with_implementation(func)")
        def with_implementation(context):
            @context.memoize_before
            async def implementation(self):
                async def async_implementation_mock(*args, **kwargs):
                    return self.value

                return async_implementation_mock

            @context.before
            async def before(self):
                mock_async_callable(
                    self.target_arg, self.callable_arg
                ).with_implementation(self.implementation)
                self.callable_target = getattr(self.real_target, self.callable_arg)

            @context.example
            async def it_calls_mocked_function(self):
                self.assertEqual(
                    await self.callable_target(*self.call_args, **self.call_kwargs),
                    self.value,
                )

            context.nest_context("return value type")

            @context.sub_context
            def with_sync_function(context):
                @context.memoize_before
                async def implementation(self):
                    def sync_implementation_mock(*args, **kwargs):
                        return self.value

                    return sync_implementation_mock

                @context.example
                async def raises_NotACoroutine_with_non_async_function(self):
                    with self.assertRaisesRegex(
                        NotACoroutine, "^Function did not return a coroutine\."
                    ):
                        await self.callable_target(*self.call_args, **self.call_kwargs)

        @context.sub_context(".with_wrapper(func)")
        def with_wrapper(context):
            @context.memoize_before
            async def wrapper(self):
                async def async_wrapper(original, *args, **kwargs):
                    return self.value

                return async_wrapper

            if has_original_callable:

                @context.before
                async def before(self):
                    mock_async_callable(
                        self.target_arg, self.callable_arg
                    ).with_wrapper(self.wrapper)
                    self.callable_target = getattr(self.real_target, self.callable_arg)

                @context.example
                async def it_calls_function(self):
                    self.assertEqual(
                        await self.callable_target(*self.call_args, **self.call_kwargs),
                        self.value,
                    )

                context.nest_context("return value type")

                @context.sub_context
                def with_sync_function(context):
                    @context.memoize_before
                    async def wrapper(self):
                        def sync_wrapper(original, *args, **kwargs):
                            return self.value

                        return sync_wrapper

                    @context.example
                    async def it_raises_NotACoroutine(self):
                        with self.assertRaisesRegex(
                            NotACoroutine, "^Function did not return a coroutine\."
                        ):
                            await self.callable_target(
                                *self.call_args, **self.call_kwargs
                            )

            else:

                @context.example
                async def it_raises_ValueError(self):
                    with self.assertRaisesRegex(
                        ValueError,
                        "^Can not wrap original callable that does not exist\.",
                    ):
                        mock_async_callable(
                            self.target_arg, self.callable_arg
                        ).with_wrapper(self.wrapper)

        if has_original_callable:

            @context.example(".to_call_original()")
            async def to_call_original(self):
                mock_async_callable(
                    self.target_arg, self.callable_arg
                ).to_call_original()
                self.assertEqual(
                    id(await self.callable_target(*self.call_args, **self.call_kwargs)),
                    id(
                        await self.original_callable(
                            *self.call_args, **self.call_kwargs
                        )
                    ),
                )

        else:

            @context.example(".to_call_original()")
            async def to_call_original(self):
                with self.assertRaisesRegex(
                    ValueError, "^Can not call original callable that does not exist\."
                ):
                    mock_async_callable(
                        self.target_arg, self.callable_arg
                    ).to_call_original()

        @context.example(".and_assert_*")
        async def and_assert(self):
            mock_async_callable(self.target_arg, self.callable_arg).to_return_value(
                None
            ).and_assert_called()
            with self.assertRaisesRegex(
                AssertionError, "^calls did not match assertion\."
            ):
                self.assert_all()

    @context.shared_context
    def sync_methods_examples(context, not_in_class_instance_method=False):
        @context.sub_context
        def and_callable_is_a_sync_instance_method(context):
            @context.memoize_before
            async def callable_arg(self):
                return "instance_method"

            if not_in_class_instance_method:

                @context.memoize_before
                async def exception_regex_message(self):
                    return "Patching an instance method at the class is not supported"

                context.merge_context(
                    "mock async callable with sync exapmles", can_mock_with_flag=False
                )
            else:
                context.merge_context("mock async callable with sync exapmles")

        @context.sub_context
        def and_callable_is_a_sync_class_method(context):
            @context.memoize_before
            async def callable_arg(self):
                return "class_method"

            context.merge_context("mock async callable with sync exapmles")

        @context.sub_context
        def and_callable_is_a_sync_static_method(context):
            @context.memoize_before
            async def callable_arg(self):
                return "static_method"

            context.merge_context("mock async callable with sync exapmles")

        @context.sub_context
        def and_callable_is_a_sync_magic_method(context):
            @context.memoize_before
            async def callable_arg(self):
                return "__str__"

            if not_in_class_instance_method:

                @context.memoize_before
                async def exception_regex_message(self):
                    return "Patching an instance method at the class is not supported"

                context.merge_context(
                    "mock async callable with sync exapmles", can_mock_with_flag=False
                )
            else:
                context.merge_context("mock async callable with sync exapmles")

    ##
    ## Contexts
    ##

    @context.sub_context
    def when_target_is_a_module(context):
        @context.memoize_before
        async def target_arg(self):
            return "tests.sample_module"

        @context.memoize_before
        async def real_target(self):
            return sample_module

        @context.sub_context
        def and_callable_is_a_function(context):
            @context.memoize_before
            async def callable_arg(self):
                return "test_function"

            context.merge_context("mock async callable with sync exapmles")

        @context.sub_context
        def and_callable_is_an_async_function(context):
            @context.before
            async def before(self):
                self.callable_arg = "async_test_function"
                self.original_callable = getattr(self.real_target, self.callable_arg)
                self.mock_async_callable_dsl = mock_async_callable(
                    self.target_arg, self.callable_arg
                )
                self.callable_target = getattr(self.real_target, self.callable_arg)
                self.call_args = ("1", "2")
                self.call_kwargs = {"kwarg1": "1", "kwarg2": "2"}

            context.merge_context("mock configuration examples")

    @context.sub_context
    def when_target_is_a_class(context):
        @context.before
        async def before(self):
            self.real_target = sample_module.Target
            self.target_arg = sample_module.Target
            self.call_args = ("1", "2")
            self.call_kwargs = {"kwarg1": "1", "kwarg2": "2"}

        context.merge_context(
            "sync methods examples", not_in_class_instance_method=True
        )

        @context.sub_context
        def and_callable_is_an_async_instance_method(context):
            @context.memoize_before
            async def callable_arg(self):
                return "async_instance_method"

            @context.example
            async def it_is_not_allowed(self):
                with self.assertRaisesRegex(
                    ValueError,
                    "Patching an instance method at the class is not supported",
                ):
                    mock_async_callable(self.target_arg, self.callable_arg)

        @context.sub_context
        def and_callable_is_an_async_class_method(context):
            @context.before
            async def before(self):
                self.callable_arg = "async_class_method"
                self.original_callable = getattr(self.real_target, self.callable_arg)
                self.mock_async_callable_dsl = mock_async_callable(
                    self.target_arg, self.callable_arg
                )
                self.callable_target = getattr(self.real_target, self.callable_arg)

            context.merge_context("mock configuration examples")

        @context.sub_context
        def and_callable_is_an_async_static_method(context):
            @context.before
            async def before(self):
                self.callable_arg = "async_static_method"
                self.original_callable = getattr(self.real_target, self.callable_arg)
                self.mock_async_callable_dsl = mock_async_callable(
                    self.target_arg, self.callable_arg
                )
                self.callable_target = getattr(self.real_target, self.callable_arg)

            context.merge_context("mock configuration examples")

        @context.sub_context
        def and_callable_is_an_async_magic_method(context):
            @context.memoize_before
            async def callable_arg(self):
                return "__aiter__"

            @context.example
            async def it_is_not_allowed(self):
                with self.assertRaisesRegex(
                    ValueError,
                    "Patching an instance method at the class is not supported",
                ):
                    mock_async_callable(self.target_arg, self.callable_arg)

    @context.sub_context
    def an_instance(context):
        @context.before
        async def before(self):
            target = sample_module.Target()
            self.real_target = target
            self.target_arg = target
            self.call_args = ("1", "2")
            self.call_kwargs = {"kwarg1": "1", "kwarg2": "2"}

        context.merge_context("sync methods examples")

        @context.sub_context
        def and_callable_is_an_async_instance_method(context):
            @context.memoize_before
            async def callable_arg(self):
                return "async_instance_method"

            @context.before
            async def before(self):
                self.original_callable = getattr(self.real_target, self.callable_arg)
                self.mock_async_callable_dsl = mock_async_callable(
                    self.target_arg, self.callable_arg
                )
                self.callable_target = getattr(self.real_target, self.callable_arg)

            context.merge_context("mock configuration examples")

        @context.sub_context
        def and_callable_is_an_async_class_method(context):
            @context.before
            async def before(self):
                self.callable_arg = "async_class_method"
                self.original_callable = getattr(self.real_target, self.callable_arg)
                self.mock_async_callable_dsl = mock_async_callable(
                    self.target_arg, self.callable_arg
                )
                self.callable_target = getattr(self.real_target, self.callable_arg)

            context.merge_context("mock configuration examples")

        @context.sub_context
        def and_callable_is_an_async_static_method(context):
            @context.before
            async def before(self):
                self.callable_arg = "async_static_method"
                self.original_callable = getattr(self.real_target, self.callable_arg)
                self.mock_async_callable_dsl = mock_async_callable(
                    self.target_arg, self.callable_arg
                )
                self.callable_target = getattr(self.real_target, self.callable_arg)

            context.merge_context("mock configuration examples")

        @context.sub_context
        def and_callable_is_an_async_magic_method(context):
            @context.before
            async def before(self):
                self.callable_arg = "__aiter__"
                self.original_callable = getattr(self.real_target, self.callable_arg)
                self.mock_async_callable_dsl = mock_async_callable(
                    self.target_arg, self.callable_arg
                )
                self.callable_target = getattr(self.real_target, self.callable_arg)
                self.call_args = ()
                self.call_kwargs = {}

            context.merge_context(
                "mock configuration examples", empty_args=True, can_yield=False
            )

    @context.sub_context
    def when_target_is_a_StrictMock(context):
        @context.before
        async def before(self):
            self.original_callable = None
            self.real_target = StrictMock(template=sample_module.Target)
            self.target_arg = self.real_target
            self.call_args = ("1", "2")
            self.call_kwargs = {"kwarg1": "1", "kwarg2": "2"}

        context.merge_context("sync methods examples")

        @context.sub_context
        def and_callable_is_an_async_instance_method(context):
            @context.before
            async def before(self):
                self.callable_arg = "async_instance_method"
                self.mock_async_callable_dsl = mock_async_callable(
                    self.target_arg, self.callable_arg
                )
                self.callable_target = getattr(self.real_target, self.callable_arg)

            context.merge_context(
                "mock configuration examples", has_original_callable=False
            )

        @context.sub_context
        def and_callable_is_an_async_class_method(context):
            @context.before
            async def before(self):
                self.callable_arg = "async_class_method"
                self.mock_async_callable_dsl = mock_async_callable(
                    self.target_arg, self.callable_arg
                )
                self.callable_target = getattr(self.real_target, self.callable_arg)

            context.merge_context(
                "mock configuration examples", has_original_callable=False
            )

        @context.sub_context
        def and_callable_is_a_async_static_method(context):
            @context.before
            async def before(self):
                self.callable_arg = "async_static_method"
                self.mock_async_callable_dsl = mock_async_callable(
                    self.target_arg, self.callable_arg
                )
                self.callable_target = getattr(self.real_target, self.callable_arg)

            context.merge_context(
                "mock configuration examples", has_original_callable=False
            )

        @context.sub_context
        def and_callable_is_an_async_magic_method(context):
            @context.before
            async def before(self):
                self.callable_arg = "__aiter__"
                self.mock_async_callable_dsl = mock_async_callable(
                    self.target_arg, self.callable_arg
                )
                self.callable_target = getattr(self.real_target, self.callable_arg)
                self.call_args = ()
                self.call_kwargs = {}

            context.merge_context(
                "mock configuration examples",
                empty_args=True,
                has_original_callable=False,
                can_yield=False,
            )
