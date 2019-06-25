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


class Target(object):  # noqa
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


original_target_class = Target
target_class_name = original_target_class.__name__


def dummy():
    pass


@context("mock_constructor()")
def mock_constructor(context):

    context.memoize("target_module", lambda self: sys.modules[__name__])
    context.memoize(
        "target_class", lambda self: getattr(self.target_module, target_class_name)
    )

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
            original_target_class is self.target_class, "Unpatching didn't work."
        )
        args = (1, 2)
        kwargs = {"3": 4, "5": 6}
        t = Target(*args, **kwargs)
        self.assertEqual(type(t), original_target_class)
        self.assertEqual(t.args, args)
        self.assertEqual(t.kwargs, kwargs)

    @context.sub_context
    def argument_validation(context):
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

    @context.example
    def it_uses_mock_callable_dsl(self):
        self.assertEqual(
            type(self.mock_constructor(self.target_module, target_class_name)),
            type(self.mock_callable(self.target_module, "dummy")),
        )

    @context.example
    def mocking_works(self):

        # Allow all other calls
        self.mock_constructor(self.target_module, target_class_name).to_call_original()
        # Mock specefic call
        mock_args = (6, 7)
        mock_kwargs = {"8": 9, "10": 11}

        # We use a wrapper here to validate that the first argument of __new__ is not
        # passed along
        def wrapper(original_callable, *args, **kwargs):
            instance = original_callable(*args, **kwargs)
            self.assertTrue(type(instance), original_target_class)
            self.assertEqual(instance.args, mock_args)
            self.assertEqual(instance.kwargs, mock_kwargs)
            return "mocked"

        self.mock_constructor(self.target_module, target_class_name).for_call(
            *mock_args, **mock_kwargs
        ).with_wrapper(wrapper)

        # And get a reference to the patched class
        target_class = getattr(self.target_module, target_class_name)

        # Generic calls works (to_call_original)
        with self.sub_example():
            original_args = ("a", "b")
            original_kwargs = {"c": "d"}
            original_instance = target_class(*original_args, **original_kwargs)
            self.assertTrue(issubclass(type(original_instance), original_target_class))
            self.assertEqual(original_instance.args, original_args)
            self.assertEqual(original_instance.kwargs, original_kwargs)

        # for_call registered calls works
        with self.sub_example():
            mocked_instance = target_class(*mock_args, **mock_kwargs)
            self.assertEqual(mocked_instance, "mocked")

    @context.example
    def accepts_module_as_string(self):
        args = (6, 7)
        kwargs = {"8": 9, "10": 11}
        self.mock_constructor(self.target_module.__name__, target_class_name).for_call(
            *args, **kwargs
        ).to_return_value("mocked")
        target_class = getattr(self.target_module, target_class_name)
        mocked_instance = target_class(*args, **kwargs)
        self.assertEqual(mocked_instance, "mocked")
