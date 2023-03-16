# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import contextlib
import sys
from typing import Optional

from testslide.dsl import Skip, context, fcontext, xcontext  # noqa: F401
from testslide.lib import TypeCheckError
from testslide.mock_callable import _MockCallableDSL
from testslide.strict_mock import StrictMock


class _PrivateClass:
    pass


class TargetParent:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        if "p2_super" in kwargs:
            self.p2_super = kwargs["p2_super"]
        if "p3_super" in kwargs:
            self.p3_super = kwargs["p3_super"]

    def p2_super_instance_method(self):
        return "p2_super_instance_method"

    def p3_super_instance_method(self):
        return "p3_super_instance_method"

    @classmethod
    def p2_super_class_method(cls):
        return "p2_super_class_method"

    @classmethod
    def p3_super_class_method(cls):
        return "p3_super_class_method"


class Target(TargetParent):
    CLASS_ATTR = "CLASS_ATTR"
    __slots__ = ("args", "kwargs", "p2_super", "p3_super")

    def __init__(self, message: Optional[str] = None, *args, **kwargs):
        self.p2_super = False
        super(Target, self).__init__(p2_super=True)

        self.p3_super = False
        super().__init__(p3_super=True)

        if message is not None:
            args = tuple([message] + list(args))
        super(Target, self).__init__(*args, **kwargs)

        self.dynamic_attr = "dynamic_attr"

    def regular_instance_method(self):
        return "regular_instance_method"

    def p2_super_instance_method(self):
        return super(Target, self).p2_super_instance_method()

    def p3_super_instance_method(self):
        return super().p3_super_instance_method()

    @staticmethod
    def static_method():
        return "static_method"

    @classmethod
    def regular_class_method(cls):
        return "regular_class_method"

    @classmethod
    def p2_super_class_method(cls):
        return super(Target, cls).p2_super_class_method()

    @classmethod
    def p3_super_class_method(cls):
        return super().p3_super_class_method()


original_target_class = Target
target_class_name = original_target_class.__name__


def function_at_module():
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
    def assertRaisesWithMessageInException(self, exception, msg):
        with self.assertRaises(exception) as cm:
            yield
        ex_msg = str(cm.exception)
        self.assertIn(
            msg,
            ex_msg,
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

    @context.shared_context
    def class_attributes(context):
        @context.example
        def attributes_are_not_affected(self):
            self.assertEqual(self.class_attribute_target.CLASS_ATTR, "CLASS_ATTR")

        @context.example
        def static_methods_are_not_affected(self):
            self.assertEqual(
                self.class_attribute_target.static_method(), "static_method"
            )

        @context.sub_context
        def class_methods(context):
            @context.example
            def are_not_affected(self):
                self.assertEqual(
                    self.class_attribute_target.regular_class_method(),
                    "regular_class_method",
                )

            @context.example("super(Target, cls) works")
            def p2_super_works(self):
                self.assertEqual(
                    self.class_attribute_target.p2_super_class_method(),
                    "p2_super_class_method",
                )

            @context.example("super() works")
            def p3_super_works(self):
                self.assertEqual(
                    self.class_attribute_target.p3_super_class_method(),
                    "p3_super_class_method",
                )

    @context.sub_context
    def patching_mechanism(context):
        @context.example
        def works_with_composition(self):
            self.mock_constructor(self.target_module, self.target_class_name).for_call(
                "1"
            ).with_wrapper(
                lambda original_callable, *args, **kwargs: original_callable("one")
            )
            self.mock_constructor(self.target_module, self.target_class_name).for_call(
                "2"
            ).with_wrapper(
                lambda original_callable, *args, **kwargs: original_callable("two")
            )

            target_one = self.get_target_class()("1")
            self.assertEqual(target_one.args, ("one",))

            target_two = self.get_target_class()("2")
            self.assertEqual(target_two.args, ("two",))

        @context.sub_context
        def original_class_attribute_access(context):
            @context.before
            def mock_constructor(self):
                self.mock_constructor(
                    self.target_module, self.target_class_name
                ).to_call_original()

            @context.example
            def can_not_create_new_instances(self):
                with self.assertRaisesWithMessageInException(
                    BaseException,
                    "Attribute getting after the class has been used with mock_constructor() is not supported!",
                ):
                    original_target_class()

            @context.example
            def can_access_class_attributes(self):
                self.assertEqual(original_target_class.CLASS_ATTR, "CLASS_ATTR")

            @context.example
            def can_call_class_methods(self):
                for name in [
                    "regular_class_method",
                    "p2_super_class_method",
                    "p3_super_class_method",
                ]:
                    self.assertEqual(getattr(original_target_class, name)(), name)

            @context.example
            def can_call_static_methods(self):
                self.assertEqual(original_target_class.static_method(), "static_method")

    @context.sub_context
    def arguments(context):
        @context.sub_context
        def module(context):
            context.memoize("args", lambda self: ("6", "7"))
            context.memoize("kwargs", lambda self: {"8": "eight", "9": "nine"})

            @context.after
            def assert_working(self):
                mocked_instance = self.get_target_class()(*self.args, **self.kwargs)
                self.assertEqual(mocked_instance, "mocked")

            @context.example
            def accepts_string(self):
                self.mock_constructor(
                    self.target_module.__name__, self.target_class_name
                ).for_call(*self.args, **self.kwargs).to_return_value("mocked")

            @context.example
            def accepts_reference(self):
                self.mock_constructor(
                    self.target_module, self.target_class_name
                ).for_call(*self.args, **self.kwargs).to_return_value("mocked")

        @context.sub_context("class")
        def klass(context):
            @context.example
            def rejects_non_string_class_name(self):
                with self.assertRaisesWithMessageInException(
                    ValueError,
                    "Second argument must be a string with the name of the class.",
                ):
                    self.mock_constructor(self.target_module, original_target_class)

            @context.example
            def rejects_non_class_targets(self):
                with self.assertRaisesWithMessageInException(
                    ValueError, "Target must be a class."
                ):
                    self.mock_constructor(self.target_module, "function_at_module")

    @context.sub_context
    def class_attributes_at_the_class(context):
        @context.memoize
        def class_attribute_target(self):
            return self.get_target_class()

        context.merge_context("class attributes")

    @context.sub_context("mock_callable() integration")
    def mock_callable_integration(context):
        @context.example
        def it_uses_mock_callable_interface(self):
            self.assertIsInstance(
                self.mock_constructor(self.target_module, self.target_class_name),
                _MockCallableDSL,
            )

        @context.example
        def registers_call_count_and_args_correctly(self):
            self.mock_constructor(self.target_module, self.target_class_name).for_call(
                "Hello", "World"
            ).to_return_value(None).and_assert_called_exactly(2)

            target_class = self.get_target_class()
            t1 = target_class("Hello", "World")
            t2 = target_class("Hello", "World")

            self.assertIsNone(t1)
            self.assertIsNone(t2)

        @context.example
        def mock_constructor_can_not_assert_if_already_received_call(self):
            mock = (
                self.mock_constructor(self.target_module, self.target_class_name)
                .for_call("Hello", "World")
                .to_return_value(None)
            )
            target_class = self.get_target_class()
            target_class("Hello", "World")
            with self.assertRaisesRegex(
                ValueError,
                "^No extra configuration is allowed after mock_constructor.+self.mock_constructor",
            ):
                mock.and_assert_called_once()

        @context.sub_context
        def behavior(context):
            @context.example(".to_call_original() works")
            def to_call_original_works(self):
                default_args = ("default",)
                specific_args = ("specific",)

                self.mock_constructor(
                    self.target_module, self.target_class_name
                ).to_call_original()
                self.mock_constructor(
                    self.target_module, self.target_class_name
                ).for_call(*specific_args).to_return_value("mocked_target")

                default_target = self.get_target_class()(*default_args)
                self.assertEqual(default_target.args, default_args)

                specific_target = self.get_target_class()(*specific_args)
                self.assertEqual(specific_target, "mocked_target")

            @context.example(".with_implementation() works")
            def with_implementation_works(self):
                args = ("1", "2")
                kwargs = {"one": "2", "two": "2"}

                def implementation(*received_args, **received_kwargs):
                    self.assertEqual(received_args, args)
                    self.assertEqual(received_kwargs, kwargs)
                    return "mock"

                self.mock_constructor(
                    self.target_module, self.target_class_name
                ).with_implementation(implementation)

                self.assertEqual(self.get_target_class()(*args, **kwargs), "mock")

            @context.sub_context(".with_wrapper()")
            def with_wrapper(context):
                context.memoize("args", lambda self: ("1", "2"))
                context.memoize("wrapped_args", lambda self: ("3", "4"))
                context.memoize("kwargs", lambda self: {"one": "1", "two": "2"})
                context.memoize(
                    "wrapped_kwargs", lambda self: {"three": "3", "four": "4"}
                )

                @context.memoize
                def target(self):
                    return self.get_target_class()(*self.args, **self.kwargs)

                @context.before
                def setup_wrapper(self):
                    def wrapper(original_callable, *args, **kwargs):
                        return original_callable(
                            *self.wrapped_args, **self.wrapped_kwargs
                        )

                    self.mock_constructor(
                        self.target_module, self.target_class_name
                    ).with_wrapper(wrapper)

                @context.example
                def wrapped_instance_is_instance_of_original_class(self):
                    self.assertIsInstance(self.target, original_target_class)

                @context.example
                def constructor_is_wrapped(self):
                    self.assertSequenceEqual(self.target.args, self.wrapped_args)
                    self.assertSequenceEqual(self.target.kwargs, self.wrapped_kwargs)

                @context.example
                def factory_works(self):
                    def factory(original_callable, message):
                        return "got: {}".format(message)

                    self.mock_constructor(
                        self.target_module, self.target_class_name
                    ).for_call("factory").with_wrapper(factory)
                    target = self.get_target_class()("factory")
                    self.assertEqual(target, "got: factory")

                @context.sub_context
                def class_attributes_at_the_instance(context):
                    context.memoize("class_attribute_target", lambda self: self.target)

                    context.merge_context("class attributes")

                @context.sub_context("Target.__init__()")
                def target_init(context):
                    @context.example("super(Target, self)")
                    def p2_super_works(self):
                        target = self.get_target_class()(p2_super=True)
                        self.assertTrue(target.p2_super)

                    @context.example("super() works")
                    def p3_super_works(self):
                        target = self.get_target_class()(p3_super=True)
                        self.assertTrue(target.p3_super)

                    @context.example
                    def can_be_called_again(self):
                        new_args = ("new", "args")
                        new_kwargs = {"new": "kwargs"}
                        self.target.__init__(*new_args, **new_kwargs)
                        self.assertEqual(self.target.args, new_args)
                        self.assertEqual(self.target.kwargs, new_kwargs)

                @context.sub_context
                def instance_methods(context):
                    @context.example
                    def it_works(self):
                        self.assertEqual(
                            self.target.regular_instance_method(),
                            "regular_instance_method",
                        )

                    @context.sub_context
                    def when_it_overloads_parent_method(context):
                        @context.example("super(Target, self) works")
                        def p2_super_works(self):
                            self.assertEqual(
                                self.target.p2_super_instance_method(),
                                "p2_super_instance_method",
                            )

                        @context.example("super() works")
                        def p3_super_works(self):
                            self.assertEqual(
                                self.target.p3_super_instance_method(),
                                "p3_super_instance_method",
                            )

    @context.sub_context
    def StrictMock_integration(context):
        @context.shared_context
        def StrictMock_tests(context):
            @context.before
            def setup(self):
                self.mock_constructor(
                    self.target_module, self.target_class_name
                ).for_call().to_return_value(self.target_mock)
                self.target = self.get_target_class()()

            @context.example
            def patching_works(self):
                self.assertIs(self.target, self.target_mock)

            @context.example("mock_callable() works")
            def mock_callable_works(self):
                self.mock_callable(
                    self.target_mock, "regular_instance_method"
                ).for_call().to_return_value("mocked")
                self.assertEqual(self.target.regular_instance_method(), "mocked")

            @context.example
            def dynamic_attributes_work(self):
                self.target_mock.dynamic_attr = "mocked_attr"
                self.assertEqual(self.target.dynamic_attr, "mocked_attr")

        @context.function
        def get_target_mock(self):
            return StrictMock(template=self.get_target_class())

        @context.sub_context
        def with_target_mock_memoized_before(context):
            @context.memoize_before
            def target_mock(self):
                return self.get_target_mock()

            context.merge_context("StrictMock tests")

        @context.sub_context
        def with_target_mock_memoized(context):
            @context.memoize
            def target_mock(self):
                return self.get_target_mock()

            context.merge_context("StrictMock tests")

    @context.example
    def private_patching_raises_valueerror(self):
        with self.assertRaises(ValueError):
            self.mock_constructor(self.target_module, _PrivateClass.__name__)

    @context.example
    def private_patching_allow_private(self):
        self.mock_constructor(
            self.target_module, _PrivateClass.__name__, allow_private=True
        ).for_call().to_return_value("mocked_private")
        _PrivateClass()

    @context.sub_context
    def type_validation(context):
        context.memoize("value", lambda self: "Target mock")
        context.memoize("type_validation", lambda self: True)

        @context.before
        def before(self):
            self.mock_constructor(
                self.target_module,
                self.target_class_name,
                type_validation=self.type_validation,
            ).to_return_value(self.value)
            self.target = getattr(self.target_module, self.target_class_name)

        @context.example
        def it_passes_with_valid_types(self):
            self.assertEqual(self.target(message="hello"), self.value)

        @context.example
        def it_fails_with_invalid_types(self):
            with self.assertRaises(TypeCheckError):
                self.target(message=1234)

        @context.sub_context("with type_validation=False")
        def with_type_validation_False(context):
            context.memoize("type_validation", lambda self: False)

            @context.example
            def it_passes_with_invalid_types(self):
                self.target(message=1234)
