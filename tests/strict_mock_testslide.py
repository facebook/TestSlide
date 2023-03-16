# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import contextlib
import copy
import functools
import inspect
import os
import re
import sys
import unittest

from testslide.dsl import Skip, context, fcontext, xcontext  # noqa: F401
from testslide.lib import TypeCheckError
from testslide.strict_mock import (
    NonAwaitableReturn,
    NonCallableValue,
    NonExistentAttribute,
    StrictMock,
    UndefinedAttribute,
    UnsupportedMagic,
)

from . import sample_module


def extra_arg_with_wraps(f):
    @functools.wraps(f)
    def wrapper(*args, **kwds):
        return f("extra", *args, **kwds)

    return wrapper


class TemplateParent:
    def __init__(self):
        self.parent_runtime_attr_from_init = True
        self.values = [1, 2, 3]

    def __str__(self):
        return "original __str__"

    def __abs__(self):
        return 33

    def __len__(self):
        return 2341

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.values:
            return self.values.pop()
        raise StopAsyncIteration

    async def __aenter__(self):
        pass

    async def __aexit__(self, exc_type, exc, tb):
        pass


class Template(TemplateParent):
    __slots__ = ["slot_attribute"]

    non_callable: str = "original value"

    def __init__(self):
        super(Template, self).__init__()
        self.runtime_attr_from_init = True
        self.attr = None

    def instance_method(self, message: str) -> str:
        return "instance_method: {}".format(message)

    async def async_instance_method(self, message: str) -> str:
        return "async_instance_method: {}".format(message)

    @staticmethod
    def static_method(message: str) -> str:
        return "static_method: {}".format(message)

    @staticmethod
    async def async_static_method(message: str) -> str:
        return "async_static_method: {}".format(message)

    @classmethod
    def class_method(cls, message: str) -> str:
        return "class_method: {}".format(message)

    @classmethod
    async def async_class_method(cls, message: str) -> str:
        return "async_class_method: {}".format(message)

    @extra_arg_with_wraps
    def instance_method_wrapped(self, extra, message):
        return "instance_method: {}".format(message)

    @extra_arg_with_wraps
    @staticmethod
    def static_method_wrapped(extra, message):
        return "static_method: {}".format(message)

    @extra_arg_with_wraps
    @classmethod
    def class_method_wrapped(cls, extra, message):
        return "class_method: {}".format(message)

    def __eq__(self, other):
        return id(self) == id(other)

    def __hash__(self):
        return id(self)


class TemplateBaseStrictMock(StrictMock):
    def __init__(self):
        super().__init__(template=Template)

    @staticmethod
    def static_method(message):
        return 101  # Wrong type

    def __len__(self):
        return 100


class TemplateStrictMock(TemplateBaseStrictMock):
    def instance_method(self, message):
        self.__instance_method_return = "mock"
        return self.__instance_method_return


class ContextManagerTemplate(Template):
    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_value, traceback):
        pass


class CallableObject:
    def __call__(self):
        pass


@context("StrictMock")  # noqa: C901
def strict_mock(context):
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
    @contextlib.contextmanager
    def assertRaisesWithRegexMessage(self, exception, rgx):
        with self.assertRaises(exception) as cm:
            yield
        ex_msg = str(cm.exception)

        if not re.search(rgx, ex_msg):
            self.assertEqual(
                ex_msg,
                rgx,
                "Expected exception {}.{} message "
                "to match regex\n{}\nbut got\n{}.".format(
                    exception.__module__, exception.__name__, repr(rgx), repr(ex_msg)
                ),
            )

    @context.memoize
    def caller_filename(self):
        current_module = sys.modules[__name__]
        filename = inspect.getsourcefile(current_module) or inspect.getfile(
            current_module
        )

        return filename

    @context.shared_context
    def can_access_attributes(context):
        @context.example
        def can_access_attributes(self):
            self.mock_function.attribute = "value"
            self.assertEqual(self.mock_function.attribute, "value")
            self.assertEqual(getattr(self.mock_function, "attribute"), "value")
            setattr(self.strict_mock, self.test_method_name, self.mock_function)
            mocked_metod = getattr(self.strict_mock, self.test_method_name)
            self.assertEqual(getattr(mocked_metod, "attribute"), "value")
            setattr(mocked_metod, "new_attribute", "new_value")
            self.assertEqual(getattr(mocked_metod, "new_attribute"), "new_value")
            delattr(mocked_metod, "new_attribute")
            self.assertFalse(hasattr(mocked_metod, "new_attribute"))

    @context.sub_context
    def without_template(context):
        context.memoize("strict_mock", lambda self: StrictMock())

        @context.memoize
        def strict_mock_rgx(self):
            return (
                "<StrictMock 0x{:02X} ".format(id(self.strict_mock))
                + re.escape(self.caller_filename)
                + r":\d+>"
            )

        context.memoize("value", lambda self: 3241234123)

        context.memoize("test_method_name", lambda self: "some_method")
        context.memoize("mock_function", lambda self: lambda: None)

        context.merge_context("can access attributes")

        @context.example
        def raises_when_an_undefined_attribute_is_accessed(self):
            name = "undefined_attribute"
            with self.assertRaisesWithRegexMessage(
                AttributeError, f"'{name}' was not set for {self.strict_mock}."
            ):
                getattr(self.strict_mock, name)

        @context.example
        def allows_mocking_any_attribute(self):
            self.strict_mock.any_attribute = self.value
            self.assertEqual(self.strict_mock.any_attribute, self.value)

        @context.example
        def allows_deleting_a_mocked_attribute(self):
            name = "attr_name"
            setattr(self.strict_mock, name, self.value)
            self.assertTrue(hasattr(self.strict_mock, name))
            delattr(self.strict_mock, name)
            with self.assertRaisesWithRegexMessage(
                AttributeError, f"'{name}' was not set for {self.strict_mock}."
            ):
                getattr(self.strict_mock, name)

        @context.example
        def allows_mocking_any_method(self):
            def value_plus(b):
                return self.value + b

            self.strict_mock.any_method = value_plus
            plus = 2341
            self.assertEqual(self.strict_mock.any_method(plus), self.value + plus)

        @context.example
        def allows_mocking_context_manager_methods(self):
            enter_mock = "something"
            self.strict_mock.__enter__ = lambda: enter_mock
            self.strict_mock.__exit__ = lambda exc_type, exc_value, traceback: None
            with self.strict_mock as target:
                self.assertEqual(target, enter_mock)

        @context.example
        def attribute_type_is_maintained(self):
            callable_attr = CallableObject()
            self.strict_mock.callable_attr = callable_attr
            attr = {1: 2}
            self.strict_mock.attr = attr
            self.assertEqual(type(self.strict_mock.callable_attr), type(callable_attr))
            self.assertEqual(type(self.strict_mock.attr), type(attr))

    @context.sub_context
    def with_a_template(context):
        @context.sub_context
        def by_subclassing_StrictMock(context):
            @context.memoize
            def strict_mock(self):
                return TemplateStrictMock()

            @context.example
            def overriding_regular_methods_work(self):
                self.assertEqual(self.strict_mock.instance_method("Hello"), "mock")

            @context.example
            def overriding_magic_methods_work(self):
                self.assertEqual(len(self.strict_mock), 100)

            @context.example
            def type_validation_works(self):
                with self.assertRaises(TypeCheckError):
                    self.strict_mock.static_method("whatever")

            @context.example
            def hash_works(self):
                d = {}
                d[self.strict_mock] = "value"
                self.assertEqual(d[self.strict_mock], "value")

            @context.example
            def cant_set_hash(self):
                with self.assertRaises(UnsupportedMagic):
                    self.strict_mock.__hash__ = lambda: 0

        @context.sub_context
        def given_as_an_argument(context):
            @context.sub_context
            def sync_attributes(context):
                context.memoize("default_context_manager", lambda self: False)
                context.memoize("type_validation", lambda self: True)

                @context.memoize
                def runtime_attr(self):
                    return "some_runtime_attr"

                @context.before
                def set_trim_path_prefix(self):
                    original_trim_path_prefix = StrictMock.TRIM_PATH_PREFIX
                    StrictMock.TRIM_PATH_PREFIX = ""

                    @self.after
                    def unpatch(self):
                        StrictMock.TRIM_PATH_PREFIX = original_trim_path_prefix

                @context.memoize
                def template(self):
                    return Template

                @context.memoize
                def strict_mock(self):
                    return StrictMock(
                        self.template,
                        runtime_attrs=[self.runtime_attr],
                        default_context_manager=self.default_context_manager,
                        type_validation=self.type_validation,
                    )

                @context.memoize
                def strict_mock_rgx(self):
                    return (
                        "<StrictMock 0x{:02X} template={} ".format(
                            id(self.strict_mock),
                            "{}.{}".format(
                                self.template.__module__, self.template.__name__
                            ),
                        )
                        + re.escape(self.caller_filename)
                        + r":\d+>"
                    )

                @context.memoize
                def mock_function(self):
                    def mock_function(message):
                        return "mock: {}".format(message)

                    return mock_function

                @context.sub_context
                def non_callable_attributes(context):
                    @context.example
                    def raises_when_an_undefined_attribute_is_accessed(self):
                        attr_name = "non_callable"
                        with self.assertRaisesWithRegexMessage(
                            UndefinedAttribute,
                            f"'{attr_name}' is not set.\n"
                            f"{self.strict_mock_rgx} must have a value set "
                            "for this attribute if it is going to be accessed.",
                        ):
                            getattr(self.strict_mock, attr_name)

                    @context.example
                    def shows_the_correct_file_and_linenum_when_raising_when_an_undefined_attribute_is_accessed(
                        self,
                    ):
                        attr_name = "non_callable"
                        with self.assertRaisesWithRegexMessage(
                            UndefinedAttribute,
                            f"'{attr_name}' is not set.\n"
                            f"{self.strict_mock_rgx} must have a value set "
                            "for this attribute if it is going to be accessed.",
                        ):
                            getattr(self.strict_mock, attr_name)

                    @context.example
                    def raises_when_an_non_existing_attribute_is_accessed(self):
                        attr_name = "non_existing_attr"
                        with self.assertRaisesWithRegexMessage(
                            AttributeError,
                            f"'{attr_name}' was not set for {self.strict_mock_rgx}.",
                        ):
                            getattr(self.strict_mock, attr_name)

                    @context.example
                    def raises_when_setting_non_existing_attributes(self):
                        attr_name = "non_existing_attr"
                        with self.assertRaisesWithRegexMessage(
                            NonExistentAttribute,
                            f"'{attr_name}' is not part of the API.*",
                        ):
                            setattr(self.strict_mock, attr_name, "whatever")

                    @context.example
                    def allows_existing_attributes_to_be_set(self):
                        new_value = "new value"
                        self.strict_mock.non_callable = new_value
                        self.assertEqual(self.strict_mock.non_callable, new_value)

                    @context.example
                    def allows_init_set_attributes_to_be_set(self):
                        new_value = lambda msg: f"hello {msg}"
                        self.strict_mock.runtime_attr_from_init = new_value
                        self.assertEqual(
                            self.strict_mock.runtime_attr_from_init("world"),
                            "hello world",
                        )

                    @context.example
                    def allows_parent_init_set_attributes_to_be_set(self):
                        new_value = "new value"
                        self.strict_mock.parent_runtime_attr_from_init = new_value
                        self.assertEqual(
                            self.strict_mock.parent_runtime_attr_from_init, new_value
                        )

                    @context.example
                    def can_set_runtime_attrs(self):
                        value = 3412
                        setattr(self.strict_mock, self.runtime_attr, value)
                        self.assertEqual(
                            getattr(self.strict_mock, self.runtime_attr), value
                        )

                    @context.example
                    def can_set_slots_attribute(self):
                        value = 3412
                        setattr(self.strict_mock, "slot_attribute", value)
                        self.assertEqual(
                            getattr(self.strict_mock, "slot_attribute"), value
                        )

                    @context.example
                    def attribute_type_is_maintained(self):
                        non_callable = "non callable"
                        self.strict_mock.non_callable = non_callable
                        self.assertEqual(
                            type(self.strict_mock.non_callable), type(non_callable)
                        )

                    @context.sub_context
                    def type_validation(context):
                        @context.example
                        def allows_setting_valid_type(self):
                            self.strict_mock.non_callable = "valid"

                        @context.example
                        def raises_with_invalid_template(self):
                            with self.assertRaises(ValueError):
                                StrictMock(dict())

                        @context.example
                        def allows_setting_valid_type_with_templated_mock(self):
                            self.strict_mock.non_callable = unittest.mock.Mock(spec=str)
                            self.strict_mock.non_callable = StrictMock(template=str)

                        @context.example
                        def allows_setting_valid_type_with_generic_mock(self):
                            self.strict_mock.non_callable = unittest.mock.Mock()
                            self.strict_mock.non_callable = StrictMock()

                        @context.example
                        def raises_TypeCheckError_when_setting_invalid_type(self):
                            with self.assertRaises(TypeCheckError):
                                self.strict_mock.non_callable = 1

                        @context.example
                        def raises_TypeCheckError_when_setting_with_mock_with_invalid_type_template(
                            self,
                        ):
                            with self.assertRaises(TypeCheckError):
                                self.strict_mock.non_callable = unittest.mock.Mock(
                                    spec=int
                                )
                            with self.assertRaises(TypeCheckError):
                                self.strict_mock.non_callable = StrictMock(template=int)

                        @context.sub_context("with type_validation=False")
                        def with_type_validation_False(context):
                            context.memoize("type_validation", lambda self: False)

                            @context.example
                            def allows_setting_invalid_type(self):
                                self.strict_mock.non_callable = 1

                            @context.example
                            def allows_setting_with_mock_with_invalid_type_template(
                                self,
                            ):
                                self.strict_mock.non_callable = unittest.mock.Mock(
                                    spec=int
                                )
                                self.strict_mock.non_callable = StrictMock(template=int)

                @context.sub_context
                def callable_attributes(context):
                    @context.shared_context
                    def callable_attribute_tests(context):
                        @context.sub_context
                        def failures(context):
                            @context.example
                            def raises_when_setting_a_non_callable_value(self):
                                with self.assertRaisesWithRegexMessage(
                                    NonCallableValue,
                                    f"'{self.test_method_name}' can not be set with a "
                                    "non-callable value.\n"
                                    f"{self.strict_mock_rgx} template class requires "
                                    "this attribute to be callable.",
                                ):
                                    setattr(
                                        self.strict_mock,
                                        self.test_method_name,
                                        "non callable",
                                    )

                            @context.example
                            def raises_when_an_undefined_method_is_accessed(self):
                                with self.assertRaisesWithRegexMessage(
                                    UndefinedAttribute,
                                    f"'{self.test_method_name}' is not set.\n"
                                    f"{self.strict_mock_rgx} must have a value set "
                                    "for this attribute if it is going to be accessed.",
                                ):
                                    getattr(self.strict_mock, self.test_method_name)

                            @context.sub_context
                            def signature_and_type_validation(context):
                                @context.example
                                def works_with_wraps(self):
                                    test_method_name = "{}_wrapped".format(
                                        self.test_method_name
                                    )
                                    setattr(
                                        self.strict_mock,
                                        test_method_name,
                                        lambda message: "mock: {}".format(message),
                                    )
                                    method = getattr(self.strict_mock, test_method_name)
                                    self.assertEqual(method("hello"), "mock: hello")

                                @context.shared_context
                                def common_examples(context, type_validation):
                                    if type_validation:

                                        @context.example
                                        def fails_on_invalid_signature_call(self):
                                            setattr(
                                                self.strict_mock,
                                                self.test_method_name,
                                                lambda message, extra: None,
                                            )
                                            with self.assertRaises(TypeError):
                                                getattr(
                                                    self.strict_mock,
                                                    self.test_method_name,
                                                )("message", "extra")

                                        @context.example
                                        def fails_on_invalid_argument_type_call(self):
                                            setattr(
                                                self.strict_mock,
                                                self.test_method_name,
                                                lambda message: None,
                                            )
                                            with self.assertRaises(TypeCheckError):
                                                getattr(
                                                    self.strict_mock,
                                                    self.test_method_name,
                                                )(1234)

                                        @context.example
                                        def fails_on_invalid_return_type(self):
                                            setattr(
                                                self.strict_mock,
                                                self.test_method_name,
                                                lambda message: 1234,
                                            )
                                            with self.assertRaises(TypeCheckError):
                                                getattr(
                                                    self.strict_mock,
                                                    self.test_method_name,
                                                )("message")

                                    else:

                                        @context.example
                                        def passes_on_invalid_argument_type_call(self):
                                            setattr(
                                                self.strict_mock,
                                                self.test_method_name,
                                                lambda message: "mock",
                                            )
                                            self.assertEqual(
                                                getattr(
                                                    self.strict_mock,
                                                    self.test_method_name,
                                                )(1),
                                                "mock",
                                            )

                                        @context.example
                                        def passes_on_invalid_return_type(self):
                                            setattr(
                                                self.strict_mock,
                                                self.test_method_name,
                                                lambda message: 1234,
                                            )
                                            self.assertEqual(
                                                getattr(
                                                    self.strict_mock,
                                                    self.test_method_name,
                                                )("message"),
                                                1234,
                                            )

                                @context.sub_context("with type_validation=True")
                                def with_type_validation_True(
                                    context,
                                ):
                                    context.merge_context(
                                        "common examples",
                                        type_validation=True,
                                    )

                                @context.sub_context("with type_validation=False")
                                def with_type_validation_False(
                                    context,
                                ):
                                    context.memoize(
                                        "type_validation", lambda self: False
                                    )

                                    context.merge_context(
                                        "common examples",
                                        type_validation=False,
                                    )

                                    @context.example
                                    def attribute_type_is_maintained(self):
                                        setattr(
                                            self.strict_mock,
                                            self.test_method_name,
                                            self.mock_function,
                                        )
                                        self.assertEqual(
                                            type(
                                                getattr(
                                                    self.strict_mock,
                                                    self.test_method_name,
                                                )
                                            ),
                                            type(self.mock_function),
                                        )

                        @context.sub_context
                        def success(context):
                            @context.example
                            def isinstance_is_true_for_template(self):
                                self.assertTrue(
                                    isinstance(self.strict_mock, self.template)
                                )
                                self.assertTrue(
                                    isinstance(self.strict_mock, self.template.mro()[1])
                                )

                            @context.sub_context
                            def method_mocking(context):
                                context.merge_context("can access attributes")

                                @context.after
                                def after(self):
                                    self.assertEqual(
                                        getattr(
                                            self.strict_mock, self.test_method_name
                                        )("hello"),
                                        "mock: hello",
                                    )

                                @context.example
                                def can_mock_with_function(self):
                                    setattr(
                                        self.strict_mock,
                                        self.test_method_name,
                                        self.mock_function,
                                    )

                                @context.example
                                def can_mock_with_lambda(self):
                                    setattr(
                                        self.strict_mock,
                                        self.test_method_name,
                                        lambda message: "mock: {}".format(message),
                                    )

                                @context.example
                                def can_mock_with_instancemethod(self):
                                    class SomeClass:
                                        def mock_method(self, message):
                                            return "mock: {}".format(message)

                                    setattr(
                                        self.strict_mock,
                                        self.test_method_name,
                                        SomeClass().mock_method,
                                    )

                    @context.example
                    def works_with_mock_callable(self):
                        """
                        Covers a case where StrictMock would fail if mock_callable() was used on a
                        class method.
                        """
                        self.mock_callable(
                            self.template, "class_method"
                        ).to_return_value(None)
                        strict_mock2 = StrictMock(self.template)
                        strict_mock2.instance_method = lambda *args, **kwargs: None

                    @context.sub_context
                    def instance_methods(context):
                        @context.before
                        def before(self):
                            self.test_method_name = "instance_method"

                        context.merge_context("callable attribute tests")

                    @context.sub_context
                    def static_methods(context):
                        @context.before
                        def before(self):
                            self.test_method_name = "static_method"

                        context.merge_context("callable attribute tests")

                    @context.sub_context
                    def class_methods(context):
                        @context.before
                        def before(self):
                            self.test_method_name = "class_method"

                        context.merge_context("callable attribute tests")

                    @context.sub_context
                    def magic_methods(context):
                        @context.example
                        def raises_when_an_undefined_magic_method_is_accessed(self):
                            with self.assertRaisesWithRegexMessage(
                                UndefinedAttribute,
                                f"'__abs__' is not set.\n"
                                f"{self.strict_mock_rgx} must have a value set "
                                "for this attribute if it is going to be accessed.",
                            ):
                                abs(self.strict_mock)

                        @context.example
                        def can_set_magic_methods(self):
                            value = 23412
                            self.strict_mock.__abs__ = lambda: value
                            self.assertEqual(abs(self.strict_mock), value)

                        @context.example("bool() works")
                        def bool_works(self):
                            with self.assertRaisesWithRegexMessage(
                                UndefinedAttribute,
                                f"'__len__' is not set.\n"
                                f"{self.strict_mock_rgx} must have a value set "
                                "for this attribute if it is going to be accessed.",
                            ):
                                bool(self.strict_mock)

                            self.strict_mock.__len__ = lambda: 0
                            self.assertEqual(bool(self.strict_mock), False)

                        @context.sub_context
                        def context_manager(context):
                            @context.memoize
                            def template(self):
                                return ContextManagerTemplate

                            @context.example
                            def context_manager_raises_UndefinedAttribute(self):
                                with self.assertRaisesWithRegexMessage(
                                    UndefinedAttribute,
                                    f"'__enter__' is not set.\n"
                                    f"{self.strict_mock_rgx} must have a value set "
                                    "for this attribute if it is going to be accessed.",
                                ):
                                    with self.strict_mock:
                                        pass

                            @context.sub_context("with default_context_manager=True")
                            def with_default_context_manager_True(context):
                                context.memoize(
                                    "default_context_manager", lambda self: True
                                )

                                @context.example
                                def it_yields_the_mock(self):
                                    with self.strict_mock as target:
                                        self.assertTrue(target is self.strict_mock)

                                @context.example
                                def works_with_exitstack(self):
                                    with contextlib.ExitStack() as exit_stack:
                                        target = exit_stack.enter_context(
                                            self.strict_mock
                                        )
                                        self.assertTrue(target is self.strict_mock)

            @context.sub_context
            def string_template(context):
                @context.example
                async def undefined_attribute(self) -> None:
                    with self.assertRaises(UndefinedAttribute):
                        StrictMock(template=str).join

                @context.example
                async def attribute_error(self) -> None:
                    with self.assertRaises(AttributeError):
                        StrictMock(template=str).garbage

            @context.sub_context
            def async_attributes(context):
                @context.memoize_before
                async def default_context_manager(self):
                    return False

                @context.memoize_before
                async def type_validation(self):
                    return True

                @context.memoize_before
                async def strict_mock(self):
                    get_strict_mock = lambda: StrictMock(
                        template=Template,
                        default_context_manager=self.default_context_manager,
                        type_validation=self.type_validation,
                    )
                    return get_strict_mock()

                @context.shared_context
                def async_method_tests(context):
                    @context.example
                    async def raises_when_setting_a_non_callable_value(self):
                        with self.assertRaisesWithRegexMessage(
                            NonCallableValue,
                            f"'{self.method_name}' can not be set with a "
                            "non-callable value.\n"
                            f"<StrictMock .+> template class requires "
                            "this attribute to be callable.",
                        ):
                            setattr(self.strict_mock, self.method_name, "not callable")

                    @context.sub_context
                    def signature_and_type_validation(context):
                        @context.shared_context
                        def common_examples(context, type_validation):
                            if type_validation:

                                @context.example
                                async def fails_on_wrong_signature_call(self):
                                    async def mock(msg):
                                        return "mock "

                                    setattr(self.strict_mock, self.method_name, mock)
                                    with self.assertRaises(TypeError):
                                        await getattr(
                                            self.strict_mock, self.method_name
                                        )("hello", "wrong")

                                @context.example
                                async def can_mock_with_async_function(self):
                                    async def mock(msg):
                                        return "mock " + msg

                                    setattr(self.strict_mock, self.method_name, mock)
                                    self.assertEqual(
                                        await getattr(
                                            self.strict_mock, self.method_name
                                        )("hello"),
                                        "mock hello",
                                    )

                                @context.example
                                async def can_not_mock_with_sync_function(self):
                                    def mock(msg):
                                        return "mock " + msg

                                    setattr(self.strict_mock, self.method_name, mock)
                                    with self.assertRaises(NonAwaitableReturn):
                                        await getattr(
                                            self.strict_mock, self.method_name
                                        )("hello"),

                                @context.example
                                async def fails_on_wrong_type_call(self):
                                    async def mock(msg):
                                        return "mock "

                                    setattr(self.strict_mock, self.method_name, mock)
                                    with self.assertRaises(TypeCheckError):
                                        await getattr(
                                            self.strict_mock, self.method_name
                                        )(1)

                                @context.example
                                async def fails_on_invalid_return_type(self):
                                    async def mock(message):
                                        return 1234

                                    setattr(
                                        self.strict_mock,
                                        self.method_name,
                                        mock,
                                    )
                                    with self.assertRaises(TypeCheckError):
                                        await getattr(
                                            self.strict_mock,
                                            self.method_name,
                                        )("message")

                            else:

                                @context.example
                                async def passes_on_wrong_signature_call(self):
                                    async def mock(msg, extra):
                                        return "mock "

                                    setattr(self.strict_mock, self.method_name, mock)
                                    await getattr(self.strict_mock, self.method_name)(
                                        "hello", "wrong"
                                    )

                                @context.example
                                async def can_mock_with_async_function(self):
                                    async def mock(msg):
                                        return "mock " + msg

                                    setattr(self.strict_mock, self.method_name, mock)
                                    self.assertEqual(
                                        await getattr(
                                            self.strict_mock, self.method_name
                                        )("hello"),
                                        "mock hello",
                                    )

                                @context.example
                                async def can_mock_with_sync_function(self):
                                    def mock(msg):
                                        return "mock " + msg

                                    setattr(self.strict_mock, self.method_name, mock)
                                    self.assertEqual(
                                        getattr(self.strict_mock, self.method_name)(
                                            "hello"
                                        ),
                                        "mock hello",
                                    )

                                @context.example
                                async def passes_on_wrong_type_call(self):
                                    async def mock(msg):
                                        return "mock "

                                    setattr(self.strict_mock, self.method_name, mock)
                                    await getattr(self.strict_mock, self.method_name)(1)

                                @context.example
                                async def passes_on_invalid_return_type(self):
                                    async def mock(message):
                                        return 1234

                                    setattr(
                                        self.strict_mock,
                                        self.method_name,
                                        mock,
                                    )
                                    self.assertEqual(
                                        await getattr(
                                            self.strict_mock,
                                            self.method_name,
                                        )("message"),
                                        1234,
                                    )

                        @context.sub_context("with type_validation=True")
                        def with_type_validation_True(
                            context,
                        ):
                            context.merge_context(
                                "common examples",
                                type_validation=True,
                            )

                        @context.sub_context("with type_validation=False")
                        def with_type_validation_False(
                            context,
                        ):
                            @context.memoize_before
                            async def type_validation(self):
                                return False

                            context.merge_context(
                                "common examples",
                                type_validation=False,
                            )

                            @context.example
                            async def attribute_type_is_maintained(self):
                                async def mock(msg):
                                    return "mock " + msg

                                setattr(self.strict_mock, self.method_name, mock)
                                self.assertEqual(
                                    type(getattr(self.strict_mock, self.method_name)),
                                    type(mock),
                                )

                @context.sub_context
                def instance_methods(context):
                    @context.memoize_before
                    async def method_name(self):
                        return "async_instance_method"

                    context.merge_context("async method tests")

                @context.sub_context
                def static_methods(context):
                    @context.memoize_before
                    async def method_name(self):
                        return "async_static_method"

                    context.merge_context("async method tests")

                @context.sub_context
                def class_methods(context):
                    @context.memoize_before
                    async def method_name(self):
                        return "async_class_method"

                    context.merge_context("async method tests")

                @context.sub_context
                def async_iterator(context):
                    @context.example
                    async def default_raises_UndefinedAttribute(self):
                        with self.assertRaisesWithRegexMessage(
                            UndefinedAttribute,
                            "'__aiter__' is not set.\n"
                            "<StrictMock .+> must have a value set "
                            "for this attribute if it is going to be accessed.",
                        ):
                            async for _ in self.strict_mock:
                                pass

                    @context.example
                    async def can_mock_async_iterator(self):
                        self.strict_mock.__aiter__ = lambda: self.strict_mock
                        expected_values = [3, 4, 5]
                        mock_values = copy.copy(expected_values)

                        async def mock():
                            if mock_values:
                                return mock_values.pop()
                            raise StopAsyncIteration

                        self.strict_mock.__anext__ = mock
                        yielded_values = []
                        async for v in self.strict_mock:
                            yielded_values.append(v)
                        self.assertEqual(
                            expected_values, list(reversed(yielded_values))
                        )

                @context.sub_context
                def async_context_manager(context):
                    @context.example
                    async def default_raises_UndefinedAttribute(self):
                        with self.assertRaisesWithRegexMessage(
                            UndefinedAttribute,
                            "'__aenter__' is not set.\n"
                            "<StrictMock .+> must have a value set "
                            "for this attribute if it is going to be accessed.",
                        ):
                            async with self.strict_mock:
                                pass

                    @context.example
                    async def can_mock_async_context_manager(self):
                        async def aenter():
                            return "yielded"

                        async def aexit(exc_type, exc_value, traceback):
                            pass

                        self.strict_mock.__aenter__ = aenter
                        self.strict_mock.__aexit__ = aexit
                        async with self.strict_mock as m:
                            assert m == "yielded"

                    @context.sub_context("default_context_manager=True")
                    def default_context_manager_True(context):
                        @context.memoize_before
                        async def default_context_manager(self):
                            return True

                        @context.example
                        async def it_yields_the_mock(self):
                            async with self.strict_mock as m:
                                assert id(self.strict_mock) == id(m)

                        @context.example
                        async def works_with_exitstack(self):
                            async with contextlib.AsyncExitStack() as exit_stack:
                                target = await exit_stack.enter_async_context(
                                    self.strict_mock
                                )
                                self.assertTrue(target is self.strict_mock)

    @context.sub_context
    def making_copies(context):
        context.memoize("strict_mock", lambda self: StrictMock(template=Template))
        context.memoize("key", lambda self: 1)
        context.memoize("value", lambda self: 2)
        context.memoize("attr", lambda self: {self.key: self.value})

        @context.before
        def set_attributes(self):
            self.strict_mock.attr = self.attr
            self.strict_mock.instance_method = lambda arg: "mock"
            self.strict_mock.__eq__ = lambda other: True

        @context.example("copy.copy()")
        def copy_copy(self):
            strict_mock_copy = copy.copy(self.strict_mock)
            self.assertEqual(id(self.strict_mock.attr), id(strict_mock_copy.attr))
            self.assertEqual(
                id(self.strict_mock.instance_method),
                id(strict_mock_copy.instance_method),
            )
            self.assertEqual(
                self.strict_mock.instance_method("hello"),
                strict_mock_copy.instance_method("hello"),
            )

        @context.example("copy.deepcopy()")
        def copy_deepcopy(self):
            strict_mock_copy = copy.deepcopy(self.strict_mock)
            self.assertEqual(self.strict_mock.attr, strict_mock_copy.attr)
            self.assertNotEqual(id(self.strict_mock.attr), id(strict_mock_copy.attr))
            self.assertEqual((self.strict_mock.attr), (strict_mock_copy.attr))
            self.assertEqual(
                self.strict_mock.instance_method("hello"),
                strict_mock_copy.instance_method("hello"),
            )
            self.assertEqual(self.strict_mock.instance_method("meh"), "mock")

    @context.sub_context("with TRIM_PATH_PREFIX set")
    def with_trim_path_prefix_set(context):
        @context.memoize
        def testslide_root(self):
            current_module = sys.modules[__name__]
            filename = inspect.getsourcefile(current_module) or inspect.getfile(
                current_module
            )
            dirname = os.sep.join(filename.split(os.sep)[:-2])
            return dirname + "/"

        @context.before
        def set_trim_path_prefix(self):
            original_trim_path_prefix = StrictMock.TRIM_PATH_PREFIX
            StrictMock.TRIM_PATH_PREFIX = self.testslide_root

            @self.after
            def unpatch(self):
                StrictMock.TRIM_PATH_PREFIX = original_trim_path_prefix

        @context.memoize
        def caller_filename(self):
            current_module = sys.modules[__name__]
            filename = inspect.getsourcefile(current_module) or inspect.getfile(
                current_module
            )
            split = filename.split(self.testslide_root)
            if len(split) == 2 and not split[0]:
                filename = split[1]
            return filename

        @context.memoize
        def template(self):
            return Template

        @context.memoize
        def strict_mock(self):
            return StrictMock(template=self.template)

        @context.example("__str__ trims prefix")
        def it_trims_prefix(self):
            self.assertTrue(
                re.search(
                    (
                        "<StrictMock 0x{:02X} template={} ".format(
                            id(self.strict_mock),
                            "{}.{}".format(
                                self.template.__module__, self.template.__name__
                            ),
                        )
                        + re.escape(self.caller_filename)
                        + r":\d+>"
                    ),
                    str(self.strict_mock),
                )
            )

    @context.sub_context
    def check_return_type_validation(context):
        @context.shared_context
        def run_context(context, target):
            @context.example
            def default_validation_at_mock_callable_level(self):
                self.mock_callable(target, "instance_method").to_return_value(1)

                if isinstance(target, StrictMock) and not target._type_validation:
                    target.instance_method(arg1="", arg2="")
                else:
                    with self.assertRaises(TypeCheckError):
                        target.instance_method(arg1="", arg2="")

            @context.example
            def enforce_validation_at_mock_callable_level(self):
                self.mock_callable(
                    target, "instance_method", type_validation=True
                ).to_return_value(1)

                with self.assertRaises(TypeCheckError):
                    target.instance_method(arg1="", arg2="")

            @context.example
            def ignore_validation_at_mock_callable_level(self):
                self.mock_callable(
                    target, "instance_method", type_validation=False
                ).to_return_value(1)
                target.instance_method(arg1="", arg2="")

        @context.sub_context
        def using_concrete_instance(context):
            context.merge_context("run context", target=sample_module.Target())

        @context.sub_context
        def using_strict_mock(context):
            context.merge_context(
                "run context", target=StrictMock(sample_module.ParentTarget)
            )

        @context.sub_context
        def using_strict_mock_with_disabled_type_validation(context):
            context.merge_context(
                "run context",
                target=StrictMock(sample_module.ParentTarget, type_validation=False),
            )
