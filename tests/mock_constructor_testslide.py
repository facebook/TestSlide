# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import sys
import contextlib

from testslide.dsl import context, xcontext, fcontext, Skip  # noqa: F401
from testslide.mock_callable import _MockCallableDSL


class BaseTarget(object):
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def calls_super(self):
        return "from super"


class Target(BaseTarget):
    def __init__(self, *args, **kwargs):
        super(Target, self).__init__(*args, **kwargs)

    def calls_super(self):
        return super(Target, self).calls_super()


if sys.version_info.major >= 3 and sys.version_info.minor >= 6:
    from typing import TypeVar, Generic

    SomeType = TypeVar("SomeType")

    class GenericTarget(Generic[SomeType]):
        pass


original_target_class = Target
target_class_name = original_target_class.__name__


def dummy():
    pass


@context("mock_constructor()")
def mock_constructor(context):

    context.memoize("target_module", lambda self: sys.modules[__name__])
    context.memoize_before("target_class_name", lambda self: target_class_name)

    @context.function
    def get_target_class(self):
        return getattr(self.target_module, self.target_class_name)

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

    @context.before
    def assert_unpatched(self):
        self.assertTrue(
            original_target_class is self.get_target_class(), "Unpatching didn't work."
        )
        args = (1, 2)
        kwargs = {"3": 4, "5": 6}
        t = Target(*args, **kwargs)
        self.assertEqual(type(t), original_target_class)
        self.assertEqual(t.args, args)
        self.assertEqual(t.kwargs, kwargs)

    @context.sub_context
    def arguments(context):
        @context.example
        def rejects_non_string_class_name(self):
            with self.assertRaisesWithMessage(
                ValueError,
                "Second argument must be a string with the name of the class.",
            ):
                self.mock_constructor(self.target_module, original_target_class)

        @context.example
        def rejects_non_class_targets(self):
            with self.assertRaisesWithMessage(ValueError, "Target must be a class."):
                self.mock_constructor(self.target_module, "dummy")

    if sys.version_info.major >= 3 and sys.version_info.minor >= 6:

        @context.sub_context
        def Generic_classes(context):
            context.memoize_before("target_class_name", lambda self: "GenericTarget")

            @context.example
            def it_works(self):
                self.mock_constructor(
                    self.target_module.__name__, self.target_class_name
                ).for_call().to_return_value("mocked")
                mocked_instance = self.get_target_class()()
                self.assertEqual(mocked_instance, "mocked")

    @context.example
    def it_uses_mock_callable_dsl(self):
        self.assertIsInstance(
            self.mock_constructor(self.target_module, self.target_class_name),
            _MockCallableDSL,
        )

    @context.sub_context("mock_callable() integration")
    def mock_callable_integration(context):
        @context.sub_context
        def assertions(context):
            @context.example
            def registers_call_count_and_args_correctly(self):
                self.mock_constructor(
                    self.target_module, self.target_class_name
                ).for_call("Hello", "World").to_return_value(
                    None
                ).and_assert_called_exactly(
                    2
                )

                target_class = self.get_target_class()
                t1 = target_class("Hello", "World")
                t2 = target_class("Hello", "World")

                self.assertIsNone(t1)
                self.assertIsNone(t2)

        @context.example
        def accepts_module_as_string(self):
            args = (6, 7)
            kwargs = {"8": 9, "10": 11}
            self.mock_constructor(
                self.target_module.__name__, self.target_class_name
            ).for_call(*args, **kwargs).to_return_value("mocked")
            mocked_instance = self.get_target_class()(*args, **kwargs)
            self.assertEqual(mocked_instance, "mocked")

        @context.sub_context
        def behavior(context):
            @context.sub_context(".with_wrapper()")
            def with_wrapper(context):
                @context.before
                def setup_wrapper(self):
                    self.mock_constructor(
                        self.target_module, self.target_class_name
                    ).to_call_original()

                    def reverse_args_wrapper(original_callable, *args, **kwargs):
                        args = reversed(args)
                        kwargs = {value: key for key, value in kwargs.items()}
                        return original_callable(*args, **kwargs)

                    self.mock_constructor(
                        self.target_module, self.target_class_name
                    ).for_call("Hello", "World", Hello="World").with_wrapper(
                        reverse_args_wrapper
                    )

                @context.memoize
                def target(self):
                    return self.get_target_class()("Hello", "World", Hello="World")

                @context.xexample
                def wrapped_instance_is_instance_of_original_class(self):
                    self.assertIsInstance(self.target, original_target_class)

                @context.example
                def constructor_is_wrapped(self):
                    self.assertSequenceEqual(self.target.args, ("World", "Hello"))
                    self.assertSequenceEqual(self.target.kwargs, {"World": "Hello"})

                @context.example("super(Target, self) works")
                def super_works(self):
                    self.assertEqual(self.target.calls_super(), "from super")

                @context.example("works with .to_call_original()")
                def works_with_to_call_original(self):
                    other_args = (1, 2)
                    other_kwargs = {"one": 1, "two": 2}
                    target = self.get_target_class()(*other_args, **other_kwargs)
                    self.assertSequenceEqual(target.args, other_args)
                    self.assertSequenceEqual(target.kwargs, other_kwargs)

                @context.example
                def factory_works(self):
                    def factory(original_callable, message):
                        return "got: {}".format(message)

                    self.mock_constructor(
                        self.target_module, self.target_class_name
                    ).for_call("factory").with_wrapper(factory)
                    target = self.get_target_class()("factory")
                    self.assertEqual(target, "got: factory")
