# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import contextlib

import testslide
from testslide.dsl import Skip, context, fcontext, xcontext  # noqa: F401
from testslide.lib import TypeCheckError
from testslide.mock_callable import (
    NotACoroutine,
    UndefinedBehaviorForCall,
    UnexpectedCallArguments,
    mock_async_callable,
)
from testslide.strict_mock import StrictMock

from . import sample_module


@context("mock_async_callable()")
def mock_async_callable_tests(context):
    ##
    ## Attributes
    ##

    @context.memoize
    def call_args(self):
        return ()

    @context.memoize
    def call_kwargs(self):
        return {}

    @context.memoize_before
    async def assertions(self):
        return []

    @context.memoize_before
    async def value(self):
        return ["mocked value"]

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

    @context.example
    async def patching_functions_in_slotted_class(self):
        t = sample_module.SomeClassWithSlots(attribute="value")
        self.mock_async_callable(t, "async_method").to_return_value(
            42
        ).and_assert_called_once()
        self.assertEqual(await t.async_method(), 42)

    @context.shared_context
    def mock_async_callable_with_sync_examples(context, can_mock_with_flag=True):
        @context.example
        async def can_not_mock(self):
            with self.assertRaisesRegex(
                ValueError,
                getattr(
                    self,
                    "exception_regex_message",
                    r"mock_async_callable\(\) can not be used with non coroutine functions\.",
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
    def sync_callable_returning_coroutine_with_mock_async_callable(context):
        @context.memoize_before
        async def implementation(self):
            async def async_implementation_mock(*args, **kwargs):
                return self.value

            return async_implementation_mock

        @context.example
        async def default_behavior(self):
            mock_async_callable(
                self.target_arg, self.callable_arg, callable_returns_coroutine=True
            )
            with self.assertRaises(UndefinedBehaviorForCall):
                await self.callable_target(*self.call_args, **self.call_kwargs)

        @context.example(".for_call()")
        async def for_call(self):
            mock_args = tuple(f"mock {str(arg)}" for arg in self.call_args)
            mock_kwargs = {k: f"mock {str(v)}" for k, v in self.call_kwargs.items()}
            mock_async_callable(
                self.target_arg, self.callable_arg, callable_returns_coroutine=True
            ).for_call(*mock_args, **mock_kwargs).with_implementation(
                lambda *_, **__: self.implementation()
            )
            self.assertEqual(
                await self.callable_target(*mock_args, **mock_kwargs), self.value
            )
            if mock_args or mock_kwargs:
                with self.assertRaises(UnexpectedCallArguments):
                    await self.callable_target(*self.call_args, **self.call_kwargs)

        @context.sub_context(".to_return_value(value)")
        def to_return_value_value(context):
            @context.example
            async def it_returns_value(self):
                mock_async_callable(
                    self.target_arg, self.callable_arg, callable_returns_coroutine=True
                ).to_return_value(self.value)
                self.callable_target = getattr(self.real_target, self.callable_arg)

                self.assertEqual(
                    await self.callable_target(*self.call_args, **self.call_kwargs),
                    self.value,
                )

            @context.example
            async def raises_TypeCheckError_when_returning_coroutine_instance(self):
                coro = self.implementation()
                mock_async_callable(
                    self.target_arg, self.callable_arg, callable_returns_coroutine=True
                ).to_return_value(coro)
                self.callable_target = getattr(self.real_target, self.callable_arg)

                with self.assertRaisesRegex(
                    TypeCheckError,
                    "^type of return must be a list; got (asyncio|coroutine)",
                ):
                    await self.callable_target(*self.call_args, **self.call_kwargs)

                # ensure the coroutine we created gets awaited on
                await coro

        @context.example(".to_raise(exception)")
        async def to_raise(self):
            mock_async_callable(
                self.target_arg, self.callable_arg, callable_returns_coroutine=True
            ).to_raise(RuntimeError("mock"))
            with self.assertRaisesWithMessage(RuntimeError, "mock"):
                await self.callable_target(*self.call_args, **self.call_kwargs)

        @context.sub_context(".with_implementation(func)")
        def with_implementation(context):
            @context.example
            async def it_calls_mocked_sync_function(self):
                mock_async_callable(
                    self.target_arg, self.callable_arg, callable_returns_coroutine=True
                ).with_implementation(
                    lambda *args, **kwargs: self.implementation(*args, **kwargs)
                )
                self.callable_target = getattr(self.real_target, self.callable_arg)

                self.assertEqual(
                    await self.callable_target(*self.call_args, **self.call_kwargs),
                    self.value,
                )

            @context.example
            async def it_calls_mocked_async_function(self):
                mock_async_callable(
                    self.target_arg, self.callable_arg, callable_returns_coroutine=True
                ).with_implementation(self.implementation)
                self.callable_target = getattr(self.real_target, self.callable_arg)

                self.assertEqual(
                    await self.callable_target(*self.call_args, **self.call_kwargs),
                    self.value,
                )

            @context.example
            async def raises_NotACoroutine_with_coroutine_func_not_instance(self):
                mock_async_callable(
                    self.target_arg, self.callable_arg, callable_returns_coroutine=True
                ).with_implementation(lambda *args, **kwargs: self.implementation)
                self.callable_target = getattr(self.real_target, self.callable_arg)

                with self.assertRaises(NotACoroutine):
                    await self.callable_target(*self.call_args, **self.call_kwargs)

            @context.sub_context
            def return_value_type(context):
                @context.example
                async def passes_with_valid_type_mocked_with_sync_function(self):
                    mock_async_callable(
                        self.target_arg,
                        self.callable_arg,
                        callable_returns_coroutine=True,
                    ).with_implementation(
                        lambda *args, **kwargs: self.implementation(*args, **kwargs)
                    )
                    self.callable_target = getattr(self.real_target, self.callable_arg)
                    await self.callable_target(*self.call_args, **self.call_kwargs)

                @context.example
                async def passes_with_valid_type_mocked_with_async_function(self):
                    mock_async_callable(
                        self.target_arg,
                        self.callable_arg,
                        callable_returns_coroutine=True,
                    ).with_implementation(self.implementation)
                    self.callable_target = getattr(self.real_target, self.callable_arg)
                    await self.callable_target(*self.call_args, **self.call_kwargs)

                @context.sub_context
                def with_invalid_return_type(context):
                    @context.memoize_before
                    async def value(self):
                        return 1

                    @context.example
                    async def raises_TypeCheckError_mocked_with_sync_function(self):
                        mock_async_callable(
                            self.target_arg,
                            self.callable_arg,
                            callable_returns_coroutine=True,
                        ).with_implementation(
                            lambda *args, **kwargs: self.implementation(*args, **kwargs)
                        )
                        self.callable_target = getattr(
                            self.real_target, self.callable_arg
                        )

                        with self.assertRaises(TypeCheckError):
                            await self.callable_target(
                                *self.call_args, **self.call_kwargs
                            )

                    @context.example
                    async def raises_TypeCheckError_mocked_with_async_function(self):
                        mock_async_callable(
                            self.target_arg,
                            self.callable_arg,
                            callable_returns_coroutine=True,
                        ).with_implementation(self.implementation)
                        self.callable_target = getattr(
                            self.real_target, self.callable_arg
                        )

                        with self.assertRaises(TypeCheckError):
                            await self.callable_target(
                                *self.call_args, **self.call_kwargs
                            )

        @context.sub_context(".with_wrapper(func)")
        def with_wrapper(context):
            @context.memoize_before
            async def wrapper(self):
                async def async_wrapper(original, *args, **kwargs):
                    return self.value

                return async_wrapper

            @context.example
            async def it_calls_mocked_sync_function(self):
                mock_async_callable(
                    self.target_arg, self.callable_arg, callable_returns_coroutine=True
                ).with_wrapper(
                    lambda original, *args, **kwargs: self.wrapper(
                        original, *args, **kwargs
                    )
                )
                self.callable_target = getattr(self.real_target, self.callable_arg)

                self.assertEqual(
                    await self.callable_target(*self.call_args, **self.call_kwargs),
                    self.value,
                )

            @context.example
            async def it_calls_mocked_async_function(self):
                mock_async_callable(
                    self.target_arg, self.callable_arg, callable_returns_coroutine=True
                ).with_wrapper(self.wrapper)
                self.callable_target = getattr(self.real_target, self.callable_arg)

                self.assertEqual(
                    await self.callable_target(*self.call_args, **self.call_kwargs),
                    self.value,
                )

            @context.example
            async def raises_NotACoroutine_with_coroutine_func_not_instance(self):
                mock_async_callable(
                    self.target_arg, self.callable_arg, callable_returns_coroutine=True
                ).with_wrapper(lambda *_, **__: self.wrapper)
                self.callable_target = getattr(self.real_target, self.callable_arg)

                with self.assertRaises(NotACoroutine):
                    await self.callable_target(*self.call_args, **self.call_kwargs)

            @context.sub_context
            def return_value_type(context):
                @context.example
                async def passes_with_valid_type_mocked_with_sync_function(self):
                    mock_async_callable(
                        self.target_arg,
                        self.callable_arg,
                        callable_returns_coroutine=True,
                    ).with_wrapper(
                        lambda original, *args, **kwargs: self.wrapper(
                            original, *args, **kwargs
                        )
                    )
                    self.callable_target = getattr(self.real_target, self.callable_arg)
                    await self.callable_target(*self.call_args, **self.call_kwargs)

                @context.example
                async def passes_with_valid_type_mocked_with_async_function(self):
                    mock_async_callable(
                        self.target_arg,
                        self.callable_arg,
                        callable_returns_coroutine=True,
                    ).with_wrapper(self.wrapper)
                    self.callable_target = getattr(self.real_target, self.callable_arg)
                    await self.callable_target(*self.call_args, **self.call_kwargs)

                @context.sub_context
                def with_invalid_return_type(context):
                    @context.memoize_before
                    async def value(self):
                        return 1

                    @context.example
                    async def raises_TypeCheckError_mocked_with_sync_function(self):
                        mock_async_callable(
                            self.target_arg,
                            self.callable_arg,
                            callable_returns_coroutine=True,
                        ).with_wrapper(
                            lambda original, *args, **kwargs: self.wrapper(
                                original, *args, **kwargs
                            )
                        )
                        self.callable_target = getattr(
                            self.real_target, self.callable_arg
                        )

                        with self.assertRaises(TypeCheckError):
                            await self.callable_target(
                                *self.call_args, **self.call_kwargs
                            )

                    @context.example
                    async def raises_TypeCheckError_mocked_with_async_function(self):
                        mock_async_callable(
                            self.target_arg,
                            self.callable_arg,
                            callable_returns_coroutine=True,
                        ).with_wrapper(self.wrapper)
                        self.callable_target = getattr(
                            self.real_target, self.callable_arg
                        )

                        with self.assertRaises(TypeCheckError):
                            await self.callable_target(
                                *self.call_args, **self.call_kwargs
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
            ).to_return_value(["mock"])
            self.assertEqual(
                await self.callable_target(*mock_args, **mock_kwargs), ["mock"]
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
                ).to_return_values([self.value, ["mock2"]])
                self.callable_target = getattr(self.real_target, self.callable_arg)

            @context.example
            async def it_returns_values(self):
                self.assertEqual(
                    await self.callable_target(*self.call_args, **self.call_kwargs),
                    self.value,
                )
                self.assertEqual(
                    await self.callable_target(*self.call_args, **self.call_kwargs),
                    ["mock2"],
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
                        NotACoroutine, r"^Function did not return a coroutine\."
                    ):
                        await self.callable_target(*self.call_args, **self.call_kwargs)

            @context.sub_context
            def with_sync_function_returning_a_coroutine(context):
                @context.memoize_before
                async def implementation(self):
                    async def async_implementation(*args, **kwargs):
                        return self.value

                    return lambda *args, **kwargs: async_implementation(*args, **kwargs)

                @context.example
                async def it_calls_mocked_function(self):
                    self.assertEqual(
                        await self.callable_target(*self.call_args, **self.call_kwargs),
                        self.value,
                    )

                context.nest_context("return value type")

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
                            NotACoroutine, r"^Function did not return a coroutine\."
                        ):
                            await self.callable_target(
                                *self.call_args, **self.call_kwargs
                            )

            else:

                @context.example
                async def it_raises_ValueError(self):
                    with self.assertRaisesRegex(
                        ValueError,
                        r"^Can not wrap original callable that does not exist\.",
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
                    ValueError, r"^Can not call original callable that does not exist\."
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
                AssertionError, r"^calls did not match assertion\."
            ):
                self.assert_all()

        @context.example
        async def mock_async_callable_can_not_assert_if_already_received_call(self):
            mock = self.mock_async_callable(
                self.target_arg, self.callable_arg
            ).to_return_value(["mocked"])
            await self.callable_target(*self.call_args, **self.call_kwargs)
            with self.assertRaisesRegex(
                ValueError,
                r"^No extra configuration is allowed after mock_async_callable.+self.mock_async_callable",
            ):
                mock.and_assert_called_once()

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
                    "mock async callable with sync examples", can_mock_with_flag=False
                )
            else:
                context.merge_context("mock async callable with sync examples")

        @context.sub_context
        def and_callable_is_a_sync_class_method(context):
            @context.memoize_before
            async def callable_arg(self):
                return "class_method"

            context.merge_context("mock async callable with sync examples")

        @context.sub_context
        def and_callable_is_a_sync_static_method(context):
            @context.memoize_before
            async def callable_arg(self):
                return "static_method"

            context.merge_context("mock async callable with sync examples")

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
                    "mock async callable with sync examples", can_mock_with_flag=False
                )
            else:
                context.merge_context("mock async callable with sync examples")

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

            context.merge_context("mock async callable with sync examples")

        @context.sub_context
        def and_callable_is_a_sync_function_returning_awaitable(context):
            context.memoize("call_args", lambda self: ("1", "2"))
            context.memoize("call_kwargs", lambda self: {"kwarg1": "1", "kwarg2": "2"})

            @context.before
            async def before(self):
                self.callable_arg = "test_function_returns_awaitable"
                self.original_callable = getattr(self.real_target, self.callable_arg)
                self.mock_async_callable_dsl = mock_async_callable(
                    self.target_arg, self.callable_arg, callable_returns_coroutine=True
                )
                self.callable_target = getattr(self.real_target, self.callable_arg)

            context.merge_context(
                "sync callable returning coroutine with mock async callable"
            )

        @context.sub_context
        def and_callable_is_a_sync_function_returning_coroutine(context):
            context.memoize("call_args", lambda self: ("1", "2"))
            context.memoize("call_kwargs", lambda self: {"kwarg1": "1", "kwarg2": "2"})

            @context.before
            async def before(self):
                self.callable_arg = "test_function_returns_coroutine"
                self.original_callable = getattr(self.real_target, self.callable_arg)
                self.mock_async_callable_dsl = mock_async_callable(
                    self.target_arg, self.callable_arg, callable_returns_coroutine=True
                )
                self.callable_target = getattr(self.real_target, self.callable_arg)

            context.merge_context(
                "sync callable returning coroutine with mock async callable"
            )

        @context.sub_context
        def and_callable_is_an_async_function(context):
            context.memoize("call_args", lambda self: ("1", "2"))
            context.memoize("call_kwargs", lambda self: {"kwarg1": "1", "kwarg2": "2"})

            @context.before
            async def before(self):
                self.callable_arg = "async_test_function"
                self.original_callable = getattr(self.real_target, self.callable_arg)
                self.mock_async_callable_dsl = mock_async_callable(
                    self.target_arg, self.callable_arg
                )
                self.callable_target = getattr(self.real_target, self.callable_arg)

            context.merge_context("mock configuration examples")

    @context.sub_context
    def when_target_is_a_class(context):
        context.memoize("call_args", lambda self: ("1", "2"))
        context.memoize("call_kwargs", lambda self: {"kwarg1": "1", "kwarg2": "2"})

        @context.before
        async def before(self):
            self.real_target = sample_module.Target
            self.target_arg = sample_module.Target

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
        context.memoize("call_args", lambda self: ("1", "2"))
        context.memoize("call_kwargs", lambda self: {"kwarg1": "1", "kwarg2": "2"})

        @context.before
        async def before(self):
            target = sample_module.Target()
            self.real_target = target
            self.target_arg = target

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
            context.memoize("call_args", lambda self: ())
            context.memoize("call_kwargs", lambda self: {})

            @context.before
            async def before(self):
                self.callable_arg = "__aiter__"
                self.original_callable = getattr(self.real_target, self.callable_arg)
                self.mock_async_callable_dsl = mock_async_callable(
                    self.target_arg, self.callable_arg
                )
                self.callable_target = getattr(self.real_target, self.callable_arg)

            context.merge_context(
                "mock configuration examples", empty_args=True, can_yield=False
            )

    @context.sub_context
    def when_target_is_a_StrictMock(context):
        context.memoize("call_args", lambda self: ("1", "2"))
        context.memoize("call_kwargs", lambda self: {"kwarg1": "1", "kwarg2": "2"})

        @context.before
        async def before(self):
            self.original_callable = None
            self.real_target = StrictMock(template=sample_module.Target)
            self.target_arg = self.real_target

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
            context.memoize("call_args", lambda self: ())
            context.memoize("call_kwargs", lambda self: {})

            @context.before
            async def before(self):
                self.callable_arg = "__aiter__"
                self.mock_async_callable_dsl = mock_async_callable(
                    self.target_arg, self.callable_arg
                )
                self.callable_target = getattr(self.real_target, self.callable_arg)

            context.merge_context(
                "mock configuration examples",
                empty_args=True,
                has_original_callable=False,
                can_yield=False,
            )
