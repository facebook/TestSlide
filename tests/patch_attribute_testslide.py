# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from testslide import StrictMock
from testslide.dsl import Skip, context, fcontext, xcontext  # noqa: F401
from testslide.lib import TypeCheckError
from testslide.patch_attribute import unpatch_all_mocked_attributes
from testslide.strict_mock import UndefinedAttribute

from . import sample_module


@context("patch_attribute()")
def patch_attribute_tests(context):
    ##
    ## Attributes
    ##

    context.memoize("new_value", lambda self: "new_value")

    ##
    ## Functions
    ##

    ##
    ## Hooks
    ##

    ##
    ## Shared Contexts
    ##

    @context.shared_context
    def patching_works(context):
        @context.function
        def strict_mock_hasattr(self, obj, name):
            try:
                return hasattr(obj, name)
            except UndefinedAttribute:
                return False

        @context.before
        def before(self):
            if self.strict_mock_hasattr(self.real_target, self.attribute):
                self.original_value = getattr(self.real_target, self.attribute)
            else:
                self.original_value = None
            self.assertNotEqual(
                self.original_value,
                self.new_value,
                "Previous test tainted this result!",
            )

        @context.after
        def after(self):
            self.assertEqual(
                getattr(self.real_target, self.attribute),
                self.new_value,
                "Patching did not work",
            )

            unpatch_all_mocked_attributes()
            if self.original_value:
                self.assertEqual(
                    getattr(self.real_target, self.attribute),
                    self.original_value,
                    "Unpatching did not work.",
                )
            else:
                self.assertFalse(
                    self.strict_mock_hasattr(self.real_target, self.attribute),
                    "Unpatching did not work",
                )

        @context.example
        def patching_works(self):
            self.patch_attribute(self.target, self.attribute, self.new_value)

        @context.example
        def double_patching_works(self):
            self.patch_attribute(self.target, self.attribute, "whatever")
            self.patch_attribute(self.target, self.attribute, self.new_value)

    @context.shared_context
    def common(context, fails_if_class_attribute):
        context.nest_context("patching works")

        @context.example
        def it_fails_if_attribute_is_callable(self):
            with self.assertRaisesRegex(ValueError, "^Attribute can not be callable*"):
                self.patch_attribute(
                    self.target, self.callable_attribute, self.new_value
                )

        if fails_if_class_attribute:

            @context.example
            def it_fails_if_attribute_is_a_class(self):
                with self.assertRaisesRegex(
                    ValueError, "^Attribute can not be a class*"
                ):
                    self.patch_attribute(
                        self.target, self.class_attribute, self.new_value
                    )

        else:

            @context.sub_context
            def with_class_attributes(context):
                context.merge_context("patching works")

        @context.sub_context
        def type_validation(context):
            @context.example
            def it_fails_if_new_value_is_of_incompatible_type(self):
                with self.assertRaises(TypeCheckError):
                    self.patch_attribute(self.target, "typedattr", 123)

            @context.example
            def it_passes_if_new_value_is_of_incompatible_type_with_type_validation_false(
                self,
            ):
                self.patch_attribute(
                    self.target, "typedattr", 123, type_validation=False
                )

            @context.example
            def it_passes_if_new_value_is_of_matching_type(
                self,
            ):
                self.patch_attribute(self.target, "typedattr", "mocked")

    ##
    ## Contexts
    ##

    @context.sub_context
    def when_target_is_a_module(context):
        context.memoize("callable_attribute", lambda self: "test_function")
        context.memoize("class_attribute", lambda self: "SomeClass")
        context.memoize("attribute", lambda self: "attribute")

        @context.sub_context
        def given_as_a_reference(context):
            context.memoize("target", lambda self: sample_module)
            context.memoize("real_target", lambda self: self.target)
            context.merge_context("common", fails_if_class_attribute=True)

        @context.sub_context
        def given_as_a_string(context):
            context.memoize("target", lambda self: "tests.sample_module")
            context.memoize("real_target", lambda self: sample_module)
            context.merge_context("common", fails_if_class_attribute=True)

    @context.sub_context
    def when_target_is_a_class(context):
        context.memoize("target", lambda self: sample_module.SomeClass)
        context.memoize("real_target", lambda self: self.target)
        context.memoize("callable_attribute", lambda self: "method")
        context.memoize("class_attribute", lambda self: "other_class_attribute")
        context.memoize("attribute", lambda self: "attribute")
        context.merge_context("common", fails_if_class_attribute=False)

        @context.sub_context
        def when_target_is_an_instance(context):
            context.memoize("target", lambda self: sample_module.SomeClass())
            context.memoize("real_target", lambda self: self.target)
            context.merge_context("common", fails_if_class_attribute=False)

            @context.sub_context
            def and_attribute_is_a_property(context):
                context.memoize("attribute", lambda self: "property_attribute")
                context.merge_context("common", fails_if_class_attribute=False)

    @context.sub_context
    def when_target_is_a_StrictMock(context):
        context.memoize("real_target", lambda self: self.target)
        context.memoize("callable_attribute", lambda self: "method")
        context.memoize("class_attribute", lambda self: "other_class_attribute")
        context.memoize("attribute", lambda self: "attribute")

        @context.sub_context
        def with_a_template(context):
            context.memoize(
                "target", lambda self: StrictMock(template=sample_module.SomeClass)
            )

            context.merge_context("common", fails_if_class_attribute=False)

        @context.sub_context
        def without_a_template(context):
            context.memoize("target", lambda self: StrictMock())
            context.merge_context("patching works")

        @context.sub_context
        def with_a_patched_runtime_attr(context):
            context.memoize(
                "target",
                lambda self: StrictMock(
                    template=sample_module.SomeClass, runtime_attrs=["runtime_attr"]
                ),
            )
            context.memoize("attribute", lambda self: "runtime_attr")
            context.merge_context("patching works")

    @context.example
    def patch_attribute_raises_valueerror_for_private(self):
        with self.assertRaises(ValueError):
            self.patch_attribute(
                sample_module.SomeClass, "_private_attr", "notsoprivate"
            )

    @context.example
    def patch_attribute_passes_for_private_with_allow_private(self):
        self.patch_attribute(
            sample_module.SomeClass, "_private_attr", "notsoprivate", allow_private=True
        )
