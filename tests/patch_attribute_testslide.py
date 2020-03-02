# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from testslide.dsl import context, xcontext, fcontext, Skip  # noqa: F401
from . import sample_module
from testslide import StrictMock
from testslide.strict_mock import UndefinedAttribute

from testslide.patch_attribute import unpatch_all_mocked_attributes


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
        @context.example
        def patching_works(self):
            def sm_hasattr(obj, name):
                try:
                    return hasattr(obj, name)
                except UndefinedAttribute:
                    return False

            if sm_hasattr(self.real_target, self.attribute):
                original_value = getattr(self.real_target, self.attribute)
            else:
                original_value = None
            self.assertNotEqual(original_value, self.new_value)
            self.patch_attribute(self.target, self.attribute, self.new_value)
            self.assertEqual(getattr(self.real_target, self.attribute), self.new_value)
            unpatch_all_mocked_attributes()
            if original_value:
                self.assertEqual(
                    getattr(self.real_target, self.attribute), original_value
                )
            else:
                self.assertFalse(sm_hasattr(self.real_target, self.attribute))

    @context.shared_context
    def common(context, fails_if_class_attribute):
        context.merge_context("patching works")

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

        @context.xexample
        def it_fails_if_new_value_is_of_incompatible_type(self):
            pass

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
