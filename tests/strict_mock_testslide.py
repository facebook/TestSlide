# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from testslide.strict_mock import StrictMock, UndefinedBehavior, NoSuchAttribute

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

    if sys.version_info[0] >= 3:

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
        if sys.version_info[0] == 2:
            ex_msg = unicode(ex_msg)  # noqa: F821
            msg = unicode(msg)  # noqa: F821
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
            def isinstance_differs(self):
                self.assertFalse(isinstance(self.strict_mock, Template))

            @context.example
            def raises_when_an_undefined_attribute_is_accessed(self):
                attr_name = "undefined_attribute"
                with self.assertRaisesWithRegexMessage(
                    UndefinedBehavior,
                    "{}:\n  ".format(self.strict_mock_rgx)
                    + re.escape(
                        "Attribute '{}' has no behavior defined.\n  ".format(attr_name)
                    )
                    + "You can define behavior by assigning a value to it.",
                ):
                    getattr(self.strict_mock, attr_name)

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
                    UndefinedBehavior,
                    "{}:\n  ".format(self.strict_mock_rgx)
                    + "Attribute '{}' has no behavior defined.\n  ".format(name)
                    + "You can define behavior by assigning a value to it.",
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
                if sys.version_info[0] == 2:
                    self.runtime_attr = self.runtime_attr.encode("utf-8")

            @context.shared_context
            def non_callable_attributes(context):
                @context.example
                def raises_when_an_undefined_attribute_is_accessed(self):
                    attr_name = "non_callable"
                    with self.assertRaisesWithRegexMessage(
                        UndefinedBehavior,
                        "{}:\n  ".format(self.strict_mock_rgx)
                        + "Attribute '{}' has no behavior defined.\n  ".format(
                            attr_name
                        )
                        + "You can define behavior by assigning a value to it.",
                    ):
                        getattr(self.strict_mock, attr_name)

                @context.example
                def raises_when_an_non_existing_attribute_is_accessed(self):
                    attr_name = "non_existing_attr"
                    with self.assertRaisesWithRegexMessage(
                        AttributeError,
                        "{}: ".format(self.strict_mock_rgx)
                        + re.escape(
                            "Can not getattr() an attribute '{}' ".format(attr_name)
                        )
                        + "that is neither part of template class Template or "
                        + re.escape(
                            "runtime_attrs=[{}].".format(repr(self.runtime_attr))
                        ),
                    ):
                        getattr(self.strict_mock, attr_name)

                @context.example
                def raises_when_setting_non_existing_attributes(self):
                    attr_name = "non_existing_attr"
                    with self.assertRaisesWithRegexMessage(
                        NoSuchAttribute,
                        "{}:\n  ".format(self.strict_mock_rgx)
                        + "No such attribute '{}'.\n  ".format(attr_name)
                        + "Can not set attribute non_existing_attr that is neither "
                        + re.escape(
                            "part of template class Template or runtime_attrs=[{}].".format(
                                repr(self.runtime_attr)
                            )
                        ),
                    ):
                        setattr(self.strict_mock, attr_name, "whatever")

                @context.example
                def allows_existing_attributes_to_be_set(self):
                    new_value = "new value"
                    self.strict_mock.non_callable = new_value
                    self.assertEqual(self.strict_mock.non_callable, new_value)

                if sys.version_info[0] >= 3:

                    @context.example
                    def allows_init_set_attributes_to_be_set(self):
                        new_value = "new value"
                        self.strict_mock.runtime_attr_from_init = new_value
                        self.assertEqual(
                            self.strict_mock.runtime_attr_from_init, new_value
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
                    self.assertEqual(getattr(self.strict_mock, "slot_attribute"), value)

            @context.shared_context
            def callable_attributes(context):
                @context.sub_context
                def failures(context):
                    @context.example
                    def raises_when_setting_a_non_callable_value(self):
                        non_callable = "non callable"
                        with self.assertRaisesWithRegexMessage(
                            ValueError,
                            "{}: ".format(self.strict_mock_rgx)
                            + "Template class attribute '{}' attribute is ".format(
                                self.test_method_name
                            )
                            + "callable and {} is not.".format(repr(non_callable)),
                        ):
                            setattr(
                                self.strict_mock, self.test_method_name, "non callable"
                            )

                    @context.example
                    def raises_when_an_undefined_method_is_accessed(self):
                        with self.assertRaisesWithRegexMessage(
                            UndefinedBehavior,
                            "{}:\n  ".format(self.strict_mock_rgx)
                            + "Attribute '{}' has no behavior defined.\n  ".format(
                                self.test_method_name
                            )
                            + "You can define behavior by assigning a value to it.",
                        ):
                            getattr(self.strict_mock, self.test_method_name)

                    @context.example
                    def raises_when_a_non_existing_method_is_accessed(self):
                        attr_name = "non_existing_method"
                        with self.assertRaisesWithRegexMessage(
                            AttributeError,
                            "{}: ".format(self.strict_mock_rgx)
                            + re.escape(
                                "Can not getattr() an attribute '{}' ".format(attr_name)
                            )
                            + "that is neither part of template class Template or "
                            + re.escape(
                                "runtime_attrs=['{}'].".format(self.runtime_attr)
                            ),
                        ):
                            getattr(self.strict_mock, attr_name)

                    @context.example
                    def raises_when_setting_non_existing_methods(self):
                        attr_name = "non_existing_method"
                        with self.assertRaisesWithRegexMessage(
                            NoSuchAttribute,
                            "{}:\n  ".format(self.strict_mock_rgx)
                            + "No such attribute '{}'.\n  ".format(attr_name)
                            + "Can not set attribute {} that is neither part of ".format(
                                attr_name
                            )
                            + re.escape(
                                "template class Template or runtime_attrs=['{}'].".format(
                                    self.runtime_attr
                                )
                            ),
                        ):
                            self.strict_mock.non_existing_method = self.mock_function

                    if sys.version_info[0] != 2:

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
                                test_method_name = "{}_extra".format(
                                    self.test_method_name
                                )
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
                        self.assertTrue(isinstance(self.strict_mock, Template))
                        self.assertTrue(isinstance(self.strict_mock, TemplateParent))

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

                        @context.example
                        def can_access_attributes(self):
                            self.mock_function.attribute = "value"
                            setattr(
                                self.strict_mock,
                                self.test_method_name,
                                self.mock_function,
                            )
                            mocked_metod = getattr(
                                self.strict_mock, self.test_method_name
                            )
                            self.assertEqual(
                                getattr(mocked_metod, "attribute"), "value"
                            )
                            setattr(mocked_metod, "new_attribute", "new_value")
                            self.assertEqual(
                                getattr(mocked_metod, "new_attribute"), "new_value"
                            )
                            delattr(mocked_metod, "new_attribute")
                            self.assertFalse(hasattr(mocked_metod, "new_attribute"))

                    @context.sub_context
                    def when_template_has_context_manager_methods(context):
                        @context.example
                        def context_management_mocked_by_default(self):
                            with self.context_manager_strict_mock as target:
                                self.assertTrue(
                                    target is self.context_manager_strict_mock
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
            def mock_instance_after_a_class_as_template(context):
                @context.before
                def before(self):
                    self.strict_mock = StrictMock(
                        Template, runtime_attrs=[self.runtime_attr]
                    )
                    self.strict_mock_rgx = (
                        "<StrictMock 0x{:02X} template={} ".format(
                            id(self.strict_mock),
                            "{}.Template".format(Template.__module__),
                        )
                        + re.escape(self.caller_filename)
                        + ":\d+>"
                    )
                    self.context_manager_strict_mock = StrictMock(
                        ContextManagerTemplate
                    )

                    def mock_function(message):
                        return "mock: {}".format(message)

                    self.mock_function = mock_function

                context.merge_context("instance attributes")

                @context.example
                def works_with_mock_callable(self):
                    """
                    Covers a case where StrictMock would fail if mock_callable() was used on a
                    class method.
                    """
                    self.mock_callable(Template, "class_method").to_return_value(None)
                    strict_mock2 = StrictMock(Template)
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
