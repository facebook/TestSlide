# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import testslide
from testslide.dsl import context, xcontext, fcontext, Skip  # noqa: F401

from testslide.mock_callable import (
    mock_callable,
    mock_async_callable,
    UndefinedBehaviorForCall,
    UnexpectedCallReceived,
    UnexpectedCallArguments,
)
import asyncio
import contextlib
from testslide.strict_mock import StrictMock
import time
import os


async def get_me_a_response():
    return "original async response"


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


class CallOrderTarget(object):
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return self.name

    async def f1(self, arg):
        return "f1: {}".format(repr(arg))

    async def f2(self, arg):
        return "f2: {}".format(repr(arg))


@context("mock_async_callable(target, callable)")  # noqa: C901
def mock_async_callable_context(context):

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

    @context.function
    def assert_all(self):
        try:
            for assertion in self.assertions:
                assertion()
        finally:
            del self.assertions[:]

    ##
    ## General tests
    ##

    @context.sub_context
    def call_order_assertion(context):
        @context.memoize
        def target1(self):
            return CallOrderTarget("target1")

        @context.memoize
        def target2(self):
            return CallOrderTarget("target2")

        @context.before
        def define_assertions(self):
            self.mock_async_callable(self.target1, "f1").for_call("step 1").to_return_value(
                "step 1 return"
            ).and_assert_called_ordered()
            self.mock_async_callable(self.target1, "f2").to_return_value(
                "step 2 return"
            ).and_assert_called_ordered()
            self.mock_async_callable(self.target2, "f1").for_call("step 3").to_return_value(
                "step 3 return"
            ).and_assert_called_ordered()

        @context.example
        async def it_passes_with_ordered_calls(self):
            self.assertEqual(await self.target1.f1("step 1"), "step 1 return")
            self.assertEqual(await self.target1.f2("step 2"), "step 2 return")
            self.assertEqual(await self.target2.f1("step 3"), "step 3 return")
            self.assert_all()

        @context.example
        async def it_fails_with_unordered_calls(self):
            self.assertEqual(await self.target1.f2("step 2"), "step 2 return")
            self.assertEqual(await self.target2.f1("step 3"), "step 3 return")
            self.assertEqual(await self.target1.f1("step 1"), "step 1 return")
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
        async def it_fails_with_partial_calls(self):
            self.assertEqual(await self.target1.f2("step 2"), "step 2 return")
            self.assertEqual(await self.target2.f1("step 3"), "step 3 return")
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
        async def other_mocks_do_not_interfere(self):
            self.mock_async_callable(self.target1, "f1").for_call(
                "unrelated 1"
            ).to_return_value("unrelated 1 return").and_assert_called_once()

            self.assertEqual(await self.target1.f1("unrelated 1"), "unrelated 1 return")

            self.mock_async_callable(self.target2, "f1").for_call(
                "unrelated 3"
            ).to_return_value("unrelated 3 return")

            self.assertEqual(await self.target1.f1("step 1"), "step 1 return")
            self.assertEqual(await self.target1.f2("step 2"), "step 2 return")
            self.assertEqual(await self.target2.f1("step 3"), "step 3 return")
            self.assert_all()

