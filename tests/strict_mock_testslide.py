# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from testslide.strict_mock import (
    StrictMock,
    UndefinedAttribute,
    NonExistentAttribute,
    NonCallableValue,
)

import contextlib
import copy
import functools
import inspect
import sys
import re
import os

from testslide.dsl import context, xcontext, fcontext, Skip  # noqa: F401


def extra_arg(f):
    @functools.wraps(f)
    def wrapper(*args, **kwds):
        return f("extra", *args, **kwds)

    return wrapper


class TemplateParent(object):
    def __init__(self):
        self.parent_runtime_attr_from_init = True

    def __str__(self):
        return "original __str__"

    def __abs__(self):
        return 33

    def __len__(self):
        return 2341


class Template(TemplateParent):

    __slots__ = ["slot_attribute"]

    non_callable = "original value"

    def __init__(self):
        super(Template, self).__init__()
        self.runtime_attr_from_init = True

    def instance_method(self, message):
        return "instance_method: {}".format(message)

    @staticmethod
    def static_method(message):
        return "static_method: {}".format(message)

    @classmethod
    def class_method(cls, message):
        return "class_method: {}".format(message)

    @extra_arg
    def instance_method_extra(self, extra, message):
        return "instance_method: {}".format(message)

    @extra_arg
    @staticmethod
    def static_method_extra(extra, message):
        return "static_method: {}".format(message)

    @extra_arg
    @classmethod
    def class_method_extra(cls, extra, message):
        return "class_method: {}".format(message)


class ContextManagerTemplate(Template):
    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_value, traceback):
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

    @context.shared_context
    def all_tests(context):
        @context.sub_context
        def without_template(context):
            @context.before
            def before(self):
                self.strict_mock = StrictMock()
                self.strict_mock_rgx = (
                    "<StrictMock 0x{:02X} ".format(id(self.strict_mock))
                    + re.escape(self.caller_filename)
                    + ":\d+>"
                )
                self.value = 2341234123

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

        @context.sub_context
        def with_a_given_template(context):
            @context.before
            def before(self):
                self.runtime_attr = "some_runtime_attr"

            @context.shared_context
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
                        f"'{attr_name}' can not be set.\n"
                        f"{self.strict_mock_rgx} template class does not have "
                        "this attribute so the mock can not have it as well.\n"
                        "See also: 'runtime_attrs' at StrictMock.__init__.",
                    ):
                        setattr(self.strict_mock, attr_name, "whatever")

                @context.example
                def allows_existing_attributes_to_be_set(self):
                    new_value = "new value"
                    self.strict_mock.non_callable = new_value
                    self.assertEqual(self.strict_mock.non_callable, new_value)

                @context.example
                def allows_init_set_attributes_to_be_set(self):
                    new_value = "new value"
                    self.strict_mock.runtime_attr_from_init = new_value
                    self.assertEqual(self.strict_mock.runtime_attr_from_init, new_value)

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
                    self.assertEqual(getattr(self.strict_mock, "slot_attribute"), value)

            @context.shared_context
            def callable_attributes(context):
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
                                self.strict_mock, self.test_method_name, "non callable"
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

                    @context.example
                    def raises_when_a_non_existing_method_is_accessed(self):
                        attr_name = "non_existing_method"
                        with self.assertRaisesWithRegexMessage(
                            AttributeError,
                            f"'{attr_name}' was not set for "
                            f"{self.strict_mock_rgx}.",
                        ):
                            getattr(self.strict_mock, attr_name)

                    @context.example
                    def raises_when_setting_non_existing_methods(self):
                        attr_name = "non_existing_method"
                        with self.assertRaisesWithRegexMessage(
                            NonExistentAttribute,
                            f"'{attr_name}' can not be set.\n"
                            f"{self.strict_mock_rgx} template class does not "
                            "have this attribute so the mock can not have it "
                            "as well.\n"
                            "See also: 'runtime_attrs' at StrictMock.__init__.",
                        ):
                            self.strict_mock.non_existing_method = self.mock_function

                    @context.sub_context
                    def signature_validation(context):
                        @context.example
                        def fails_on_wrong_signature_call(self):
                            setattr(
                                self.strict_mock,
                                self.test_method_name,
                                lambda message, extra: None,
                            )
                            with self.assertRaises(TypeError):
                                getattr(self.strict_mock, self.test_method_name)(
                                    "message", "extra"
                                )

                        @context.example
                        def works_with_wraps(self):
                            test_method_name = "{}_extra".format(self.test_method_name)
                            setattr(
                                self.strict_mock,
                                test_method_name,
                                lambda message: "mock: {}".format(message),
                            )
                            method = getattr(self.strict_mock, test_method_name)
                            self.assertEqual(method("hello"), "mock: hello")

                @context.sub_context
                def success(context):
                    @context.example
                    def isinstance_is_true_for_template(self):
                        self.assertTrue(isinstance(self.strict_mock, self.template))
                        self.assertTrue(
                            isinstance(self.strict_mock, self.template.mro()[1])
                        )

                    @context.sub_context
                    def method_mocking(context):
                        @context.after
                        def after(self):
                            self.assertEqual(
                                getattr(self.strict_mock, self.test_method_name)(
                                    "hello"
                                ),
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
                            class SomeClass(object):
                                def mock_method(self, message):
                                    return "mock: {}".format(message)

                            setattr(
                                self.strict_mock,
                                self.test_method_name,
                                SomeClass().mock_method,
                            )

            @context.shared_context
            def instance_attributes(context):

                context.nest_context("non callable attributes")

                @context.sub_context
                def callable_attributes(context):
                    @context.sub_context
                    def instance_methods(context):
                        @context.before
                        def before(self):
                            self.test_method_name = "instance_method"

                        context.merge_context("callable attributes")

                    @context.sub_context
                    def static_methods(context):
                        @context.before
                        def before(self):
                            self.test_method_name = "static_method"

                        context.merge_context("callable attributes")

                    @context.sub_context
                    def class_methods(context):
                        @context.before
                        def before(self):
                            self.test_method_name = "class_method"

                        context.merge_context("callable attributes")

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

                            @context.sub_context("with default_context_manager=True")
                            def with_default_context_manager_True(context):
                                @context.memoize
                                def strict_mock(self):
                                    return StrictMock(template=self.template)

                                @context.example
                                def context_manager_works(self):
                                    with self.strict_mock as target:
                                        self.assertTrue(target is self.strict_mock)

                            @context.sub_context("with default_context_manager=False")
                            def with_default_context_manager_False(context):
                                @context.memoize
                                def strict_mock(self):
                                    return StrictMock(
                                        template=self.template,
                                        default_context_manager=False,
                                    )

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

            @context.sub_context
            def mock_instance_after_a_class_as_template(context):
                @context.memoize
                def template(self):
                    return Template

                @context.memoize
                def strict_mock(self):
                    return StrictMock(self.template, runtime_attrs=[self.runtime_attr])

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
                        + ":\d+>"
                    )

                @context.memoize
                def mock_function(self):
                    def mock_function(message):
                        return "mock: {}".format(message)

                    return mock_function

                context.merge_context("instance attributes")

                @context.example
                def works_with_mock_callable(self):
                    """
                    Covers a case where StrictMock would fail if mock_callable() was used on a
                    class method.
                    """
                    self.mock_callable(self.template, "class_method").to_return_value(
                        None
                    )
                    strict_mock2 = StrictMock(self.template)
                    strict_mock2.instance_method = lambda *args, **kwargs: None

            # @context.xsub_context
            # def mock_instance_after_any_object_as_template(context):
            #     context.merge_context('instance attributes')
            #
            # @context.xsub_context
            # def mock_class_after_a_class_as_template(context):
            #     context.nest_context('non callable attributes')
            #
            #     @context.sub_context
            #     def callable_attributes(context):
            #
            #         @context.sub_context
            #         def instance_methods(context):
            #
            #             @context.xexample
            #             def it_raises(self):
            #                 pass
            #
            #         @context.sub_context
            #         def static_methods(context):
            #             context.merge_context('callable attributes')
            #
            #         @context.sub_context
            #         def class_methods(context):
            #             context.merge_context('callable attributes')
            #
            #     @context.sub_context
            #     def creating_new_instances(context):
            #
            #         @context.sub_context('__call__ not set')
            #         def call_not_set(context):
            #
            #             @context.xexample
            #             def it_raises(self):
            #                 pass
            #
            #         @context.sub_context('__call__ set')
            #         def call_set(context):
            #
            #             @context.xexample
            #             def it_return_call_result(self):
            #                 pass

        @context.sub_context
        def making_copies(context):

            context.memoize("strict_mock", lambda self: StrictMock())

            context.memoize("key", lambda self: 1)
            context.memoize("value", lambda self: 2)
            context.memoize("attr", lambda self: {self.key: self.value})

            @context.before
            def set_attributes(self):
                self.strict_mock.attr = self.attr

            @context.example("copy.copy()")
            def copy_copy(self):
                strict_mock_copy = copy.copy(self.strict_mock)
                self.assertEqual(self.strict_mock.attr, strict_mock_copy.attr)
                # it is a shallow copy
                strict_mock_copy.attr[self.key] = None
                self.assertEqual(self.strict_mock.attr, strict_mock_copy.attr)

            @context.example("copy.deepcopy()")
            def copy_deepcopy(self):
                strict_mock_copy = copy.deepcopy(self.strict_mock)
                self.assertEqual(self.strict_mock.attr, strict_mock_copy.attr)
                # it is a deep copy
                strict_mock_copy.attr[self.key] = None
                self.assertNotEqual(self.strict_mock.attr, strict_mock_copy.attr)

    @context.sub_context
    def with_trim_path_prefix(context):
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
            StrictMock.TRIM_PATH_PREFIX = self.testslide_root

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

        context.merge_context("all tests")

    @context.sub_context
    def without_trim_path_prefix(context):
        @context.before
        def set_trim_path_prefix(self):
            StrictMock.TRIM_PATH_PREFIX = ""

        @context.memoize
        def caller_filename(self):
            current_module = sys.modules[__name__]
            filename = inspect.getsourcefile(current_module) or inspect.getfile(
                current_module
            )
            return filename

        context.merge_context("all tests")
