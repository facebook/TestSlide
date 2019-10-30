# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import unittest

from unittest.mock import Mock, call, patch

from testslide import Context, AggregatedExceptions, reset
from testslide.dsl import context, xcontext, fcontext
import os
import subprocess


class SomeTestCase(unittest.TestCase):
    """
    Used to test TestSlide and unittest.TestCase integration.
    """

    CALLS = []

    def setUp(self):
        self.CALLS.append("setUp")
        super(SomeTestCase, self).setUp()

    tearDown_calls = 0

    def tearDown(self):
        self.CALLS.append("tearDown")
        super(SomeTestCase, self).tearDown()

    @classmethod
    def setUpClass(cls):
        cls.CALLS.append("setUpClass")
        super(SomeTestCase, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        cls.CALLS.append("tearDownClass")
        super(SomeTestCase, cls).tearDownClass()

    def test_should_not_run(self):
        self.CALLS.append("test_should_not_run")


class SomeTestCase2(unittest.TestCase):
    """
    Used to test TestSlide and unittest.TestCase integration.
    """

    CALLS = []

    def setUp(self):
        self.CALLS.append("setUp2")
        super(SomeTestCase2, self).setUp()

    tearDown_calls = 0

    def tearDown(self):
        self.CALLS.append("tearDown2")
        super(SomeTestCase2, self).tearDown()

    @classmethod
    def setUpClass(cls):
        cls.CALLS.append("setUpClass2")
        super(SomeTestCase2, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        cls.CALLS.append("tearDownClass2")
        super(SomeTestCase2, cls).tearDownClass()

    def test_should_not_run(self):
        self.CALLS.append("test_should_not_run2")


class SimulatedFailure(Exception):
    def __init__(self, message, second_message):
        """
        This method purposely accepts an extra argument to catch failures when
        reraising exceptions.
        """
        super(SimulatedFailure, self).__init__(message, second_message)
        self.message = message
        self.second_message = second_message

    def __str__(self):
        return "{} {}".format(self.message, self.second_message)


class TestDSLBase(unittest.TestCase):
    def setUp(self):
        reset()

    def run_first_context_first_example(self):
        Context.all_top_level_contexts[0].all_examples[0]()

    def run_first_context_all_examples(self):
        for example in Context.all_top_level_contexts[0].all_examples:
            example()

    def _print_context_hierarchy(self, contexts=None, indent=""):
        if contexts is None:
            print("")
            contexts = Context.all_top_level_contexts
        for ctx in contexts:
            print(
                '{}Context: "{}" (skip={}, focus={})'.format(
                    indent, str(ctx), ctx.skip, ctx.focus
                )
            )
            for name in ctx.shared_contexts.keys():
                print('  {}Shared context: "{}"'.format(indent, name))
            for example in ctx.all_examples:
                print('  {}Example: "{}"'.format(indent, example))
            if ctx.children_contexts:
                self._print_context_hierarchy(
                    ctx.children_contexts, "{}  ".format(indent)
                )


class TestDSLContext(TestDSLBase):

    # Context creation

    def test_can_be_named_from_decorator(self):
        """
        Contexts can be named with an argument for @context decorator.
        """
        name = "context name"

        @context(name)
        def whatever(_):
            pass

        self.assertEqual(str(Context.all_top_level_contexts[0]), name)

    def test_can_be_named_from_function(self):
        """
        Contexts can have its name extracted from the function decorated by
        @context, thus saving typing.
        """

        @context
        def Context_name_from_Function(_):
            pass

        self.assertEqual(
            str(Context.all_top_level_contexts[0]), "Context name from Function"
        )

    def test_multiple_top_contexts(self):
        """
        We can have multiple top contexts declared.
        """

        @context
        def first_context(_):
            pass

        @context
        def second_context(_):
            pass

        self.assertEqual(str(Context.all_top_level_contexts[0]), "first context")
        self.assertEqual(str(Context.all_top_level_contexts[1]), "second context")

    def test_can_nest_contexts(self):
        """
        Contexts can be nested arbitrarily below a top context.
        """

        context_names = [
            "top context name",
            "first nested context name",
            "second nested context name",
        ]

        @context(context_names[0])
        def top(context):
            @context.sub_context(context_names[1])
            def sub1(context):
                @context.sub_context(context_names[2])
                def sub2(context):
                    pass

        expected_nested_context_names = context_names

        registered_nested_context_names = []
        registered_nested_context_names.append(str(Context.all_top_level_contexts[0]))
        registered_nested_context_names.append(
            str(Context.all_top_level_contexts[0].children_contexts[0])
        )
        registered_nested_context_names.append(
            str(
                Context.all_top_level_contexts[0]
                .children_contexts[0]
                .children_contexts[0]
            )
        )

        self.assertEqual(expected_nested_context_names, registered_nested_context_names)

    def test_cant_call_context_function(self):
        """
        Context functions are not meant to be called directly.
        """

        @context
        def not_callable(_):
            pass

        with self.assertRaisesRegex(
            BaseException, "This function should not be called outside test code."
        ):
            not_callable(None)

    # Duplicate names

    def test_cant_create_top_contexts_with_same_name(self):
        """
        User should get a clear error when trying to create two contexts with
        the same name at top level.
        """
        with self.assertRaisesRegex(
            RuntimeError, "A context with the same name is already defined"
        ):

            @context
            def top_context(context):
                pass

            @context("top context")
            def whatever(_):
                pass

    def test_can_create_nested_contexts_with_same_name(self):
        """
        It is allowed to have a nested context wih the same name as its parent.
        """

        @context
        def same_name(context):
            @context.sub_context
            def same_name(_):
                pass

        self.assertEqual(str(Context.all_top_level_contexts[0]), "same name")
        self.assertEqual(
            str(Context.all_top_level_contexts[0].children_contexts[0]), "same name"
        )

    def test_cant_create_nested_contexts_with_same_name(self):
        """
        User should get a clear error when trying to create two contexts with
        the same name at the same level.
        """
        with self.assertRaisesRegex(
            RuntimeError, "A context with the same name is already defined"
        ):

            @context
            def top_context(context):
                @context.sub_context
                def repeated_name(_):
                    pass

                @context.sub_context("repeated name")
                def whatever(_):
                    pass

    # Focus and skip

    def test_skip_contexts(self):
        """
        Contexts can be marked as skipped by using the prefix "x" to either
        a top or nested context. Children contexts inherits parent's skip
        setting.
        """

        @context
        def not_skipped(context):
            @context.xsub_context
            def skipped(context):
                @context.sub_context
                def inherits_skip_setting_from_parent(_):
                    pass

            @context.sub_context
            def not_skipped(context):
                pass

        @xcontext
        def skipped(context):
            @context.sub_context
            def not_skipped(context):
                @context.sub_context
                def not_skipped(_):
                    pass

        self.assertFalse(Context.all_top_level_contexts[0].skip)
        self.assertTrue(Context.all_top_level_contexts[0].children_contexts[0].skip)
        self.assertFalse(Context.all_top_level_contexts[0].children_contexts[1].skip)
        # Inherits skip from parent
        self.assertTrue(
            Context.all_top_level_contexts[0]
            .children_contexts[0]
            .children_contexts[0]
            .skip
        )

        self.assertTrue(Context.all_top_level_contexts[1].skip)
        # Inherits skip from parent
        self.assertTrue(Context.all_top_level_contexts[1].children_contexts[0].skip)
        # Inherits skip from parent
        self.assertTrue(
            Context.all_top_level_contexts[1]
            .children_contexts[0]
            .children_contexts[0]
            .skip
        )

    def test_focus_contexts(self):
        """
        Contexts can be marked as focused by using the prefix "f" to either
        a top or nested context. Children contexts inherits parent's focus
        setting.
        """

        @context
        def not_focused(context):
            @context.fsub_context
            def focused(context):
                @context.sub_context
                def inherits_focus_setting_from_parent(_):
                    pass

            @context.sub_context
            def not_focused(context):
                pass

        @fcontext
        def focused(context):
            @context.sub_context
            def not_focused(context):
                @context.sub_context
                def not_focused(_):
                    pass

        self.assertFalse(Context.all_top_level_contexts[0].focus)
        self.assertTrue(Context.all_top_level_contexts[0].children_contexts[0].focus)
        self.assertFalse(Context.all_top_level_contexts[0].children_contexts[1].focus)
        # Inherits focus from parent
        self.assertTrue(
            Context.all_top_level_contexts[0]
            .children_contexts[0]
            .children_contexts[0]
            .focus
        )

        self.assertTrue(Context.all_top_level_contexts[1].focus)
        # Inherits focus from parent
        self.assertTrue(Context.all_top_level_contexts[1].children_contexts[0].focus)
        # Inherits focus from parent
        self.assertTrue(
            Context.all_top_level_contexts[1]
            .children_contexts[0]
            .children_contexts[0]
            .focus
        )


class TestDSLSharedContext(TestDSLBase):

    # Shared contexts

    def test_shared_context_named_from_decorator(self):
        """
        Shared contexts can be declared with the @context.shared_context
        decorator and its name is fetch from the decorated function.
        """

        @context
        def top(context):
            @context.shared_context
            def Shared_context(context):
                pass

        self.assertEqual(len(Context.all_top_level_contexts[0].all_shared_contexts), 1)
        self.assertEqual(
            list(Context.all_top_level_contexts[0].shared_contexts.keys()),
            ["Shared context"],
        )

    def test_shared_context_named_from_function(self):
        """
        Shared contexts can be declared with the @context.shared_context
        decorator and its name can be given as a decorator argument.
        """

        @context
        def top(context):
            @context.shared_context("Shared context")
            def whatever(self):
                pass

        self.assertEqual(len(Context.all_top_level_contexts[0].all_shared_contexts), 1)
        self.assertEqual(
            list(Context.all_top_level_contexts[0].shared_contexts.keys()),
            ["Shared context"],
        )

    def test_cant_create_two_shared_contexts_with_same_name(self):
        """
        User should get a clear error when trying to create two shared contexts
        with the same name.
        """
        with self.assertRaisesRegex(
            RuntimeError, "A shared context with the same name is already defined"
        ):

            @context
            def top(context):
                @context.shared_context
                def Shared_context(context):
                    pass

                @context.shared_context("Shared context")
                def whatever(self):
                    pass

    def test_inherit_shared_context(self):
        """
        Nested contexts inherits shared contexts declared in its parents.
        """

        @context
        def top(context):
            @context.shared_context
            def Shared_context(context):
                pass

            @context.sub_context
            def sub(context):
                pass

        self.assertEqual(
            list(
                Context.all_top_level_contexts[0]
                .children_contexts[0]
                .all_shared_contexts.keys()
            ),
            ["Shared context"],
        )

    # Merge shared context

    def test_merge_shared_context(self):
        """
        Shared contexts can be merged inside a context with
        context.merge_context(name).
        """

        @context
        def top(context):
            @context.shared_context
            def Shared_context(context, arg_passed=False):

                assert arg_passed

                @context.example
                def Shared_example(self):
                    pass

            @context.sub_context
            def sub(context):
                context.merge_context("Shared context", arg_passed=True)

        self.assertEqual(
            str(Context.all_top_level_contexts[0].children_contexts[0].examples[0]),
            "Shared example",
        )

    def test_merge_invalid_shared_context(self):
        """
        User gets a clear error message when trying to merge an invalid
        shared context.
        """
        invalid_name = "invalid shared context name"
        with self.assertRaisesRegex(
            TypeError, 'Shared context "{}" does not exist'.format(invalid_name)
        ):

            @context
            def top(context):
                @context.shared_context
                def Shared_context(context):
                    @context.example
                    def Shared_example(self):
                        pass

                @context.sub_context
                def sub(context):
                    context.merge_context(invalid_name)

    def test_cant_merge_shared_context_on_top(self):
        """
        It makes no sense to merge a shared context on top level.
        """
        with self.assertRaisesRegex(
            TypeError, "Can not merge a shared context without a parent context"
        ):
            context.merge_context("whatever")

    # Nest shared context

    def test_nest_shared_context(self):
        """
        Shared conetxts can be nested below other contexts with
        context.nest_context(name). A new context is created below, with the
        same name as the shared context.
        """

        @context
        def top(context):
            @context.shared_context
            def Shared_context(context, arg_passed=False):

                assert arg_passed

                @context.example
                def Shared_example(self):
                    pass

            @context.sub_context
            def sub(context):
                context.nest_context("Shared context", arg_passed=True)

        self.assertEqual(
            [
                str(Context.all_top_level_contexts[0]),
                str(Context.all_top_level_contexts[0].children_contexts[0]),
                str(
                    Context.all_top_level_contexts[0]
                    .children_contexts[0]
                    .children_contexts[0]
                ),
                str(
                    Context.all_top_level_contexts[0]
                    .children_contexts[0]
                    .children_contexts[0]
                    .examples[0]
                ),
            ],
            ["top", "sub", "Shared context", "Shared example"],
        )

    def test_nest_invalid_shared_context(self):
        """
        User should get a clear error message when trying to nest an invalid
        shared context name.
        """
        invalid_name = "invalid shared context name"
        with self.assertRaisesRegex(
            TypeError, 'Shared context "{}" does not exist'.format(invalid_name)
        ):

            @context
            def top(context):
                @context.shared_context
                def Shared_context(context):
                    @context.example
                    def Shared_example(self):
                        pass

                @context.sub_context
                def sub(context):
                    context.nest_context(invalid_name)

    def test_cant_nest_shared_context_on_top(self):
        """
        It is not allowed to nest a shared context directly on top level.
        """
        with self.assertRaisesRegex(
            TypeError, "Can not nest a shared context without a parent context"
        ):
            context.nest_context("whatever")


class TestDSLHelperFunction(TestDSLBase):
    def test_helper_functions(self):
        """
        Arbitrary functions can be declared to example execution scope with
        @context.function decorator.
        """

        helper_mock = Mock()

        @context
        def top(context):
            @context.function
            def helper_function(self, msg):
                helper_mock(msg)

            @context.example
            def can_call_helper(self):
                self.helper_function("Hello")

        self.run_first_context_first_example()
        helper_mock.assert_called_once_with("Hello")

    def test_helper_function_cant_be_called_directly(self):
        """
        Helper functions are not meant to be called directly.
        """
        with self.assertRaisesRegex(
            BaseException, "This function should not be called outside test code."
        ):

            @context
            def top(context):
                @context.function
                def helper(self, msg):
                    pass

                helper()

    def test_cant_create_two_helper_functions_with_same_name(self):
        """
        User gets a clear error mesasge when trying to create two helper
        functions with the same name.
        """
        with self.assertRaisesRegex(
            AttributeError, 'Attribute "helper" already set for context "top"'
        ):

            @context
            def top(context):
                @context.function
                def helper(self, msg):
                    pass

                @context.function  # noqa: F811
                def helper(self, msg):
                    pass

    def test_cant_create_helper_function_on_top(self):
        """
        It is not allowed to create a helper function outside of a context.
        """
        with self.assertRaisesRegex(
            TypeError, "Can not create functions without a parent context"
        ):

            @context.function
            def helper(self):
                pass


class TestDSLMergeTestCase(TestDSLBase):
    def test_merge_test_case(self):
        """
        merge_test_case allows to integrate existing unittest.TestCase classes
        much like merge_context(). Only hook methods (setup, teardown etc) will
        be used, no exisitng examples will be imported.
        """

        calls = []

        with patch.object(SomeTestCase, "CALLS", new=calls):
            with patch.object(SomeTestCase2, "CALLS", new=calls):

                @context
                def top(context):
                    @context.around
                    def first_around_hook(self, example):
                        calls.append("first around before")
                        example()
                        calls.append("first around after")

                    @context.around
                    def second_around_hook(self, example):
                        calls.append("second around before")
                        example()
                        calls.append("second around after")

                    context.merge_test_case(SomeTestCase, "some_test_case")

                    context.merge_test_case(SomeTestCase2, "some_test_case2")

                    @context.before
                    def before(self):
                        calls.append("before")

                    @context.after
                    def after(self):
                        calls.append("after")

                    @context.example
                    def example(self):
                        calls.append("example")
                        assert issubclass(type(self.some_test_case), SomeTestCase)
                        assert issubclass(type(self.some_test_case2), SomeTestCase2)

                self.run_first_context_first_example()

            self.assertEqual(
                calls,
                [
                    "first around before",
                    "second around before",
                    "setUpClass",
                    "setUp",
                    "setUpClass2",
                    "setUp2",
                    "before",
                    "example",
                    "after",
                    "tearDown2",
                    "tearDownClass2",
                    "tearDown",
                    "tearDownClass",
                    "second around after",
                    "first around after",
                ],
            )

    def test_report_merged_test_case_failures(self):
        """
        Properly report failures with TestCase merging.
        """

        calls = []

        with patch.object(SomeTestCase, "CALLS", new=calls):

            @context
            def top(context):
                @context.around
                def first_around_hook(self, example):
                    calls.append("first around before")
                    example()
                    calls.append("first around after")

                @context.around
                def second_around_hook(self, example):
                    calls.append("second around before")
                    example()
                    calls.append("second around after")

                context.merge_test_case(SomeTestCase, "some_test_case")

                @context.before
                def before(self):
                    calls.append("before")

                @context.after
                def after(self):
                    calls.append("after")

                @context.example
                def example(self):
                    calls.append("example")
                    raise SimulatedFailure("Simulated failure", "(extra)")

            with self.assertRaises(SimulatedFailure):
                self.run_first_context_first_example()

            self.assertEqual(
                calls,
                [
                    "first around before",
                    "second around before",
                    "setUpClass",
                    "setUp",
                    "before",
                    "example",
                    "after",
                    "tearDown",
                    "tearDownClass",
                ],
            )

    def test_cant_merge_test_case_on_top(self):
        with self.assertRaisesRegex(
            TypeError, "Can not merge a TestCase without a parent context"
        ):
            context.merge_test_case(SomeTestCase)


class TestDSLMemoizedAttribute(TestDSLBase):
    def test_memoize_attribute(self):
        """
        Arbitrary attributes can be defined to example execution scope, by
        decorating a function with @context.memoize. The attribute will have
        the same name as the function, and its value will be materialized on
        the first access.
        """

        mock = Mock()

        @context
        def top(context):

            value = 1
            memoized = []

            @context.memoize
            def attribute_name(self):
                memoized.append(True)
                return value + 1

            @context.example
            def attribute_is_memoized(self):
                assert not memoized
                mock(self.attribute_name)
                assert memoized
                mock(self.attribute_name)

        self.run_first_context_first_example()
        self.assertEqual(mock.mock_calls, [call(2), call(2)])

    def test_memoize_attribute_as_lambda(self):
        """
        Memoize attributes can be declared by passing the attribute name and
        a lambda.
        """
        mock = Mock()

        @context
        def top(context):

            value = 1

            context.memoize("attribute_name", lambda _: value + 1)

            @context.example
            def attribute_is_memoized(self):
                mock(self.attribute_name)
                mock(self.attribute_name)

        self.run_first_context_first_example()
        self.assertEqual(mock.mock_calls, [call(2), call(2)])

    def test_memoize_attribute_with_kwargs(self):
        """
        Memoize attributes can be declared by passing attributes as kwargs.
        """
        mock = Mock()

        @context
        def top(context):

            value = 1

            context.memoize(
                attribute1=lambda _: value + 1, attribute2=lambda _: value + 2
            )

            @context.example
            def attribute_is_memoized(self):
                mock(self.attribute1)
                mock(self.attribute2)

        self.run_first_context_first_example()
        self.assertEqual(mock.mock_calls, [call(2), call(3)])

    def test_cant_call_memoizable_functions_directly(self):
        """
        It is not allowed to call memoized attributes directly.
        """
        with self.assertRaisesRegex(
            BaseException, "This function should not be called outside test code."
        ):

            @context
            def top(context):
                @context.memoize
                def attribute(self, msg):
                    pass

                attribute()

    def test_cant_create_two_memoizable_with_same_name(self):
        """
        User should get a clear error when trying to declare two memoized
        attributes with the same name.
        """
        with self.assertRaisesRegex(
            AttributeError, 'Attribute "name" already set for context "top"'
        ):

            @context
            def top(context):
                @context.memoize
                def name(self, msg):
                    pass

                @context.memoize  # noqa: F811
                def name(self, msg):
                    pass


class TestDSLMemoizedBeforeAttribute(TestDSLBase):
    def test_memoize_before_attribute(self):
        """
        Similar to @context.memoize, but materializes the value at a before
        hook.
        """

        mock = Mock()

        @context
        def top(context):

            value = 1
            memoized = []

            @context.memoize_before
            def attribute_name(self):
                memoized.append(True)
                return value + 1

            @context.example
            def attribute_is_memoized(self):
                assert memoized
                mock(self.attribute_name)
                mock(self.attribute_name)

        self.run_first_context_first_example()
        self.assertEqual(mock.mock_calls, [call(2), call(2)])

    def test_memoize_before_attribute_as_lambda(self):
        """
        Similar to @context.memoize with a lambda, but materializes the value at
        a before hook.
        """
        mock = Mock()

        @context
        def top(context):

            value = 1
            memoized = []

            def creator(self):
                memoized.append(True)
                return value + 1

            context.memoize_before("attribute_name", creator)

            @context.example
            def attribute_is_memoized(self):
                assert memoized
                mock(self.attribute_name)
                mock(self.attribute_name)

        self.run_first_context_first_example()
        self.assertEqual(mock.mock_calls, [call(2), call(2)])

    def test_cant_call_memoize_before_functions_directly(self):
        """
        Similar to @context.memoize.
        """
        with self.assertRaisesRegex(
            BaseException, "This function should not be called outside test code."
        ):

            @context
            def top(context):
                @context.memoize_before
                def attribute(self, msg):
                    pass

                attribute()

    def test_cant_create_two_memoize_before_with_same_name(self):
        """
        Similar to @context.memoize.
        """
        with self.assertRaisesRegex(
            AttributeError, 'Attribute "name" already set for context "top"'
        ):

            @context
            def top(context):
                @context.memoize_before
                def name(self, msg):
                    pass

                @context.memoize_before  # noqa: F811
                def name(self, msg):
                    pass


class TestDSLBeforeHook(TestDSLBase):
    def test_before_hook(self):
        """
        Arbitrary before hooks can be declared with @context.before decorator.
        They will be called in the order defined before each example.
        """

        mock = Mock()

        @context
        def top(context):
            @context.before
            def first_before_hook(self):
                mock("first before")

            @context.before
            def second_before_hook(self):
                mock("second before")

            @context.example
            def with_before_hook(self):
                mock("example")

        self.run_first_context_first_example()
        self.assertEqual(
            mock.mock_calls,
            [call("first before"), call("second before"), call("example")],
        )

    def test_before_hook_as_lambda(self):
        mock = Mock()

        @context
        def top(context):

            context.before(lambda _: mock("first before"))
            context.before(lambda _: mock("second before"))

            @context.example
            def with_before_hook(self):
                mock("example")

        self.run_first_context_first_example()
        self.assertEqual(
            mock.mock_calls,
            [call("first before"), call("second before"), call("example")],
        )

    def test_before_hook_fail(self):
        """
        When one before hook fails, stop example execution.
        """
        mock = Mock()

        @context
        def top(context):
            @context.before
            def first_before_hook(self):
                mock("first before")

            @context.before
            def second_before_hook(self):
                mock("second before")

            @context.before
            def third_before_hook(self):
                raise SimulatedFailure("Simulated failure", "(extra)")

            @context.example
            def with_before_hook(self):
                mock("example")

        try:
            self.run_first_context_first_example()
        except SimulatedFailure:
            pass
        self.assertEqual(mock.mock_calls, [call("first before"), call("second before")])

    def test_cant_call_before_function_directly(self):
        """
        It is not allowed to call a before hook directly.
        """
        with self.assertRaisesRegex(
            BaseException, "This function should not be called outside test code."
        ):

            @context
            def top_context(context):
                @context.before
                def not_callable(self):
                    pass

                not_callable(None)

    def test_cant_define_before_on_top(self):
        """
        Before hooks are only allowed within a context.
        """
        with self.assertRaisesRegex(
            TypeError, "Can not register before hook without a parent context"
        ):

            @context.before
            def not_allowed(self):
                pass


class TestDSLAfterHook(TestDSLBase):
    def test_after_hook(self):
        """
        After hooks can be declared with @context.after decorator. They will
        be called in the order defined after each example.
        """
        mock = Mock()

        @context
        def top(context):
            @context.after
            def first_after_hook(self):
                mock("first after")

            @context.after
            def second_after_hook(self):
                mock("second after")

            @context.example
            def with_after_hook(self):
                mock("example")

        self.run_first_context_first_example()
        self.assertEqual(
            mock.mock_calls,
            [call("example"), call("second after"), call("first after")],
        )

    def test_after_hook_as_lambda(self):
        mock = Mock()

        @context
        def top(context):

            context.after(lambda _: mock("first after"))
            context.after(lambda _: mock("second after"))

            @context.example
            def with_after_hook(self):
                mock("example")

        self.run_first_context_first_example()
        self.assertEqual(
            mock.mock_calls,
            [call("example"), call("second after"), call("first after")],
        )

    def test_after_hook_from_example(self):
        """
        After hooks can be declared with @self.after decorator from an example.
        They will be called in the order defined after each example.
        """
        mock = Mock()

        @context
        def top(context):
            @context.example
            def with_after_hook(self):
                @self.after
                def first_after_hook(self):
                    mock("first after")

                @self.after
                def second_after_hook(self):
                    mock("second after")

                mock("example")

        self.run_first_context_first_example()
        self.assertEqual(
            mock.mock_calls,
            [call("example"), call("second after"), call("first after")],
        )

    def test_after_hook_fail(self):
        """
        When one of the after hooks fails, all other after hooks are still
        executed and all failures are aggregated into a AggregatedExceptions
        exception.
        """
        mock = Mock()

        @context
        def top(context):
            @context.after
            def first_after_hook(self):
                mock("first after")
                raise SimulatedFailure("first failure", "(extra)")

            @context.after
            def second_after_hook(self):
                mock("second after")
                raise SimulatedFailure("second failure", "(extra)")

            @context.after
            def third_after_hook(self):
                mock("third after")
                raise SimulatedFailure("third failure", "(extra)")

            @context.example
            def with_after_hook(self):
                mock("example")

        try:
            self.run_first_context_first_example()
        except AggregatedExceptions as agg_ex:
            self.assertEqual(
                [str(after_ex) for after_ex in agg_ex.exceptions],
                [
                    "third failure (extra)",
                    "second failure (extra)",
                    "first failure (extra)",
                ],
            )
        self.assertEqual(
            mock.mock_calls,
            [
                call("example"),
                call("third after"),
                call("second after"),
                call("first after"),
            ],
        )

    def test_cant_call_after_function_directly(self):
        """
        It is not allowed to call an after hook directly.
        """
        with self.assertRaisesRegex(
            BaseException, "This function should not be called outside test code."
        ):

            @context
            def top_context(context):
                @context.after
                def not_callable(self):
                    pass

                not_callable(None)

    def test_cant_define_after_on_top(self):
        """
        After hooks can only be called within a declared context.
        """
        with self.assertRaisesRegex(
            TypeError, "Can not register after hook without a parent context"
        ):

            @context.after
            def not_allowed(self):
                pass

    def test_assertions_run_after_after_hooks(self):
        """
        Assertions must be the last thing executed, allowing any registered
        after hooks to fulfill them.
        """

        @context
        def top(context):
            context.memoize("target", lambda self: Mock())

            @context.after
            def call_target(self):
                self.target.something()

            @context.example
            def assert_something_called(self):
                self.mock_callable(self.target, "something").to_return_value(
                    None
                ).and_assert_called_once()

        self.run_first_context_first_example()


class TestDSLAroundHook(TestDSLBase):
    def test_around_hook(self):  # NOQA C91
        """
        Around hooks can be declared with @context.around decorator. The
        decorated funcion must call example() once. The code before
        example() will be executed before all before hooks, and the code
        after example() will be executed after all after hooks. Multiple
        around hooks can be defined, and they will be wrapped by all previously
        declared hooks.
        """
        mock = Mock()

        @context
        def top(context):
            @context.around
            def first_top_around(self, example):
                mock("first top around start")
                example()
                mock("first top around end")

            @context.around
            def second_top_around(self, example):
                mock("second top around start")
                example()
                mock("second top around end")

            context.before(lambda _: mock("first top before"))
            context.before(lambda _: mock("second top before"))
            context.after(lambda _: mock("first top after"))
            context.after(lambda _: mock("second top after"))

            @context.sub_context
            def inner(context):
                @context.around
                def first_inner_around(self, example):
                    mock("first inner around start")
                    example()
                    mock("first inner around end")

                @context.around
                def second_inner_around(self, example):
                    mock("second inner around start")
                    example()
                    mock("second inner around end")

                context.before(lambda _: mock("first inner before"))
                context.before(lambda _: mock("second inner before"))
                context.after(lambda _: mock("first inner after"))
                context.after(lambda _: mock("second inner after"))

                @context.example
                def example(self):
                    mock("example")

        self.run_first_context_first_example()
        self.assertEqual(
            mock.mock_calls,
            [
                call("first top around start"),
                call("second top around start"),
                call("first inner around start"),
                call("second inner around start"),
                call("first top before"),
                call("second top before"),
                call("first inner before"),
                call("second inner before"),
                call("example"),
                call("second inner after"),
                call("first inner after"),
                call("second top after"),
                call("first top after"),
                call("second inner around end"),
                call("first inner around end"),
                call("second top around end"),
                call("first top around end"),
            ],
        )

    def test_around_failure_aborts_execution(self):
        """
        If the code before example() in an around hook fails, the
        example execution is aborted.
        """
        mock = Mock()

        @context
        def top(context):
            @context.around
            def first_around_hook(self, example):
                mock("first around before")
                raise SimulatedFailure("first around before failure", "(extra)")

            @context.around
            def second_around_hook(self, example):
                mock("second around before")
                example()
                mock("second around after")

            @context.before
            def before(self):
                mock("before")

            @context.after
            def after(self):
                mock("after")

            @context.example
            def with_around_hook(self):
                mock("example")

        try:
            self.run_first_context_first_example()
        except SimulatedFailure:
            pass
        self.assertEqual(mock.mock_calls, [call("first around before")])

    def test_around_cant_be_called_directly(self):
        """
        It is not allowed to call around hooks directly.
        """
        with self.assertRaisesRegex(
            BaseException, "This function should not be called outside test code"
        ):

            @context
            def top(context):
                @context.around
                def not_callable(self, example):
                    pass

                not_callable(None)

    def test_around_cant_be_set_on_top(self):
        """
        Around hooks must be declared within a declared context.
        """
        with self.assertRaisesRegex(
            TypeError, "Can not register around hook without a parent context"
        ):

            @context.around
            def invalid(self, example):
                pass

    def test_can_set_arbitrary_attributes(self):
        """
        Within before, after and around hooks, it is allowed to defined
        arbitrary attributes to self, that can be referenced later.
        """
        mock = Mock()

        @context
        def top(context):
            @context.around
            def around(self, example):
                self.around = "around"
                example()

            @context.before
            def before(self):
                self.before = "before"

            @context.after
            def after(self):
                mock(self.example)

            @context.example
            def can_access_attributes(self):
                mock(self.around)
                mock(self.before)
                self.example = "example"

        self.run_first_context_first_example()
        self.assertEqual(
            mock.mock_calls, [call("around"), call("before"), call("example")]
        )

    def test_fails_if_example_not_called(self):
        @context
        def top(context):
            @context.around
            def broken_around(self, example):
                pass  # without calling example()

            @context.example
            def whatever(self):
                pass

        with self.assertRaisesRegex(
            RuntimeError, "Around hook .*broken_around.* did not execute example code"
        ):
            self.run_first_context_first_example()


class TestExample(TestDSLBase):
    def test_can_be_named_from_decorator(self):
        """
        Examples can be declared with @context.example(name) decorator.
        """
        name = "example name"

        @context
        def top_context(context):
            @context.example(name)
            def whatever(_):
                pass

        self.assertEqual(str(Context.all_top_level_contexts[0].examples[0]), name)

    def test_can_be_named_from_function(self):
        """
        Examples can be declared with @context.example decorator, and its
        name is taken from the decorated function.
        """

        @context
        def top_context(context):
            @context.example
            def Example_name(_):
                pass

        self.assertEqual(
            str(Context.all_top_level_contexts[0].examples[0]), "Example name"
        )

    def test_cant_create_example_outside_context(self):
        """
        Examples must be declared within a context.
        """
        with self.assertRaisesRegex(
            TypeError, "Can not create example without a parent context"
        ):

            @context.example
            def whatever(_):
                pass

    def test_skip_with_xexample(self):
        """
        An example can be declared as skip with @context.xexample.
        """

        @context
        def top_context(context):
            @context.xexample
            def skip_with_xexample(_):
                pass

            @context.example(skip=True)
            def skip_with_skip_arg(_):
                pass

            @context.example("skip_with_name_and_skip_arg", skip=True)
            def skip_with_name_and_skip_arg(_):
                pass

            @context.example(skip_unless=False)
            def skip_with_skip_unless_arg(_):
                pass

            @context.example("skip_with_name_and_skip_unless_arg", skip_unless=False)
            def skip_with_name_and_skip_unless_arg(_):
                pass

        self.assertTrue(Context.all_top_level_contexts[0].examples)
        for example in Context.all_top_level_contexts[0].examples:
            self.assertTrue(example.skip)

    def test_inherits_skip_from_xcontext(self):
        """
        Exmaples inherit skip setting from parent context.
        """

        @xcontext
        def skipped_context(context):
            @context.example
            def also_skipped(_):
                pass

        self.assertTrue(Context.all_top_level_contexts[0].examples[0].skip)

    def test_focus_with_fexample(self):
        """
        An example can be focused as with @context.fexample.
        """

        @context
        def top_context(context):
            @context.fexample
            def focused(_):
                pass

        self.assertTrue(Context.all_top_level_contexts[0].examples[0].focus)

    def test_inherits_focus_from_fcontext(self):
        """
        Exmaples inherit focus setting from parent context.
        """

        @fcontext
        def focused_context(context):
            @context.example
            def also_focused(_):
                pass

        self.assertTrue(Context.all_top_level_contexts[0].examples[0].focus)

    def test_cant_call_example_function(self):
        """
        It is not allowed to call example function directly.
        """
        with self.assertRaisesRegex(
            BaseException, "This function should not be called outside test code."
        ):

            @context
            def top_context(context):
                @context.example
                def not_callable(_):
                    pass

                not_callable(None)

    def test_cant_create_two_with_same_name(self):
        """
        User should get a clear error message if two examples with the same
        name are declared within the same context.
        """
        with self.assertRaisesRegex(
            RuntimeError, "An example with the same name is already defined"
        ):

            @context
            def top_context(context):
                @context.example
                def same_name(_):
                    pass

                @context.example("same name")
                def whatever(_):
                    pass

    def test_can_call_unittest_assert_methods(self):
        """
        Python's unittest.TestCase assert* methods are available to use.
        """

        @context
        def unittest_assert_methods(context):
            @context.example
            def has_assert_true(self):
                self.assertTrue(True)

        self.run_first_context_first_example()

    def test_can_define_sub_examples(self):
        """
        Sub examples can be defined, and failures are aggregated at the end.
        """

        ex1 = AssertionError("Sub failure 1")
        ex2 = AssertionError("Sub failure 2")
        exfinal = RuntimeError("Final failure")

        @context
        def sub_examples(context):
            @context.example
            def can_define_sub_examples(self):
                with self.sub_example():
                    assert True

                with self.sub_example():
                    raise ex1

                with self.sub_example():
                    raise ex2

                raise exfinal

        try:
            self.run_first_context_first_example()
        except AggregatedExceptions as e:
            self.assertEqual(len(e.exceptions), 3)
            self.assertTrue(ex1 in e.exceptions)
            self.assertTrue(ex2 in e.exceptions)
            self.assertTrue(exfinal in e.exceptions)
        else:
            raise AssertionError("Expected test to fail")


class TestMockCallableIntegration(TestDSLBase):
    def test_mock_callable_integration(self):
        @context
        def fail_top(context):
            @context.sub_context
            def fail_sub_context(context):
                @context.example
                def expect_fail(self):
                    self.mock_callable("os", "getcwd").for_call().to_return_value(
                        "mocked_cwd"
                    ).and_assert_called_once()

        @context
        def pass_top(context):
            @context.sub_context
            def pass_sub_context(context):
                @context.example
                def expect_pass(self):
                    self.mock_callable("os", "getcwd").for_call().to_return_value(
                        "mocked_cwd"
                    ).and_assert_called_once()
                    assert os.getcwd() == "mocked_cwd"

        examples = {}

        for all_top_level_context in Context.all_top_level_contexts:
            for example in all_top_level_context.all_examples:
                examples[example.name] = example

        examples["expect pass"]()

        with self.assertRaisesRegex(AssertionError, "calls did not match assertion"):
            examples["expect fail"]()


class TestMockConstructorIntegration(TestDSLBase):
    def test_mock_constructor_integration(self):
        @context
        def fail_top(context):
            @context.sub_context
            def fail_sub_context(context):
                @context.example
                def expect_fail(self):
                    self.mock_constructor("subprocess", "Popen").for_call(
                        ["cmd"]
                    ).to_return_value("mocked_popen").and_assert_called_once()

        @context
        def pass_top(context):
            @context.sub_context
            def pass_sub_context(context):
                @context.example
                def expect_pass(self):
                    self.mock_constructor("subprocess", "Popen").for_call(
                        ["cmd"]
                    ).to_return_value("mocked_popen").and_assert_called_once()
                    assert subprocess.Popen(["cmd"]) == "mocked_popen"

        examples = {}

        for all_top_level_context in Context.all_top_level_contexts:
            for example in all_top_level_context.all_examples:
                examples[example.name] = example

        examples["expect pass"]()

        with self.assertRaisesRegex(AssertionError, "calls did not match assertion"):
            examples["expect fail"]()
