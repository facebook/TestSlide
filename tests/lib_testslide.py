# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from typing import Type, TypeVar
from testslide.dsl import context, xcontext, fcontext, Skip  # noqa: F401
import testslide.lib
import testslide.mock_callable
from . import sample_module
from testslide import StrictMock
import unittest.mock


@context("_validate_callable_arg_types")
def _validate_callable_arg_types(context):
    @context.memoize
    def skip_first_arg(self):
        return False

    @context.memoize
    def callable_template(self):
        return sample_module.test_function

    @context.function
    def assert_passes(self, *args, **kwargs):
        testslide.lib._validate_callable_arg_types(
            self.skip_first_arg, self.callable_template, args, kwargs
        )

    @context.function
    def assert_fails(self, *args, **kwargs):
        with self.assertRaisesRegex(TypeError, "Call with incompatible argument types"):
            testslide.lib._validate_callable_arg_types(
                self.skip_first_arg, self.callable_template, args, kwargs
            )

    @context.example
    def passes_for_canonical_call_with_valid_types(self):
        self.assert_passes("arg1", "arg2", kwarg1="kwarg1", kwarg2="kwarg2")

    @context.example
    def fails_for_canonical_with_invalid_types(self):
        self.assert_fails(1, "arg2", kwarg1="kwarg1", kwarg2="kwarg2")
        self.assert_fails("arg1", 2, kwarg1="kwarg1", kwarg2="kwarg2")
        self.assert_fails("arg1", "arg2", kwarg1=1, kwarg2="kwarg2")
        self.assert_fails("arg1", "arg2", kwarg1="kwarg1", kwarg2=2)

    @context.example
    def passes_for_kwargs_as_args_call_with_valid_types(self):
        self.assert_passes("arg1", "arg2", "kwarg1", "kwarg2")
        self.assert_passes("arg1", "arg2", "kwarg1", kwarg2="kwarg2")

    @context.example
    def fails_for_kwargs_as_args_with_invalid_types(self):
        self.assert_fails("arg1", "arg2", 1, "kwarg2")
        self.assert_fails("arg1", "arg2", "kwarg1", 2)
        self.assert_fails("arg1", "arg2", 1, kwarg2="kwarg2")
        self.assert_fails("arg1", "arg2", "kwargs1", kwarg2=2)

    @context.example
    def passes_for_args_as_kwargs_call_with_valid_types(self):
        self.assert_passes("arg1", arg2="arg2", kwarg1="kwarg1", kwarg2="kwarg2")
        self.assert_passes(arg1="arg1", arg2="arg2", kwarg1="kwarg1", kwarg2="kwarg2")

    @context.example
    def fails_for_args_as_kwargs_with_invalid_types(self):
        self.assert_fails(arg1=1, arg2="arg2", kwarg1="kwarg1", kwarg2="kwarg2")
        self.assert_fails(arg1="arg1", arg2=2, kwarg1="kwarg1", kwarg2="kwarg2")
        self.assert_fails(arg1="arg1", arg2="arg2", kwarg1=1, kwarg2="kwarg2")
        self.assert_fails(arg1="arg1", arg2="arg2", kwarg1="kwarg1", kwarg2=2)

    @context.example
    def gives_correct_error_message_for_invalid_types(self):
        with self.assertRaises(
            TypeError,
            msg=(
                "Call with incompatible argument types:\n"
                "  'arg1': type of arg1 must be str; got int instead\n"
                "  'arg2': type of arg2 must be str; got int instead\n"
                "  'kwarg1': type of kwarg1 must be str; got int instead\n"
                "  'kwarg2': type of kwarg2 must be str; got int instead"
            ),
        ):
            testslide.lib._validate_callable_arg_types(
                self.skip_first_arg, self.callable_template, (1, 2, 3, 4), {}
            )

    @context.example("Invalid return Type raises TypeError")
    def assert_raised_typeerror(self):
        target_obj = sample_module.InvalidReturnType()

        fake_runner = testslide.mock_callable._ReturnValueRunner(
            target=target_obj,
            method="invalid_return_type_function",
            original_callable=target_obj.invalid_return_type_function,
            value=target_obj.invalid_return_type_function(),
        )
        with self.assertRaises(
            TypeError,
                msg=(
                    f"Call with incorrect return types, expected <class 'int'> got str.\n"
                    f"Call initiated from object: {repr(target_obj)}"
            )
        ):
            testslide.lib._validate_return_type(
                fake_runner, "str"
            )

    @context.example("works with object.__new__")
    def works_with_object_new(self):
        self.callable_template = object.__new__
        self.assert_passes(1, 2, 3, four=5, six=6)

    @context.sub_context
    def instance_method(context):
        @context.memoize
        def callable_template(self):
            target = sample_module.SomeClass()
            return target.instance_method_with_star_args

        @context.example
        def passes_for_args_as_starargs_call(self):
            self.assert_passes("d", "x", "ddd", a=False, b=2, c=None)

    @context.sub_context("testslide.StrictMock")
    def testslide_strict_mock(context):
        @context.example
        def passes_with_valid_template(self):
            strict_mock = StrictMock(template=str)
            self.assert_passes(strict_mock, "arg2", kwarg1="kwarg1", kwarg2="kwarg2")
            self.assert_passes("arg1", strict_mock, kwarg1="kwarg1", kwarg2="kwarg2")
            self.assert_passes("arg1", "arg2", kwarg1=strict_mock, kwarg2="kwarg2")
            self.assert_passes("arg1", "arg2", kwarg1="kwarg1", kwarg2=strict_mock)

        @context.example
        def passes_without_template(self):
            strict_mock = StrictMock()
            self.assert_passes(strict_mock, "arg2", kwarg1="kwarg1", kwarg2="kwarg2")
            self.assert_passes("arg1", strict_mock, kwarg1="kwarg1", kwarg2="kwarg2")
            self.assert_passes("arg1", "arg2", kwarg1=strict_mock, kwarg2="kwarg2")
            self.assert_passes("arg1", "arg2", kwarg1="kwarg1", kwarg2=strict_mock)

        @context.example
        def fails_with_invalid_template(self):
            strict_mock = StrictMock(template=int)
            self.assert_fails(strict_mock, "arg2", kwarg1="kwarg1", kwarg2="kwarg2")
            self.assert_fails("arg1", strict_mock, kwarg1="kwarg1", kwarg2="kwarg2")
            self.assert_fails("arg1", "arg2", kwarg1=strict_mock, kwarg2="kwarg2")
            self.assert_fails("arg1", "arg2", kwarg1="kwarg1", kwarg2=strict_mock)

    @context.sub_context("unittest.mock.Mock")
    def unittest_mock_mock(context):
        @context.example
        def passes_with_valid_spec(self):
            mock = unittest.mock.Mock(spec=str)
            self.assert_passes(mock, "arg2", kwarg1="kwarg1", kwarg2="kwarg2")
            self.assert_passes("arg1", mock, kwarg1="kwarg1", kwarg2="kwarg2")
            self.assert_passes("arg1", "arg2", kwarg1=mock, kwarg2="kwarg2")
            self.assert_passes("arg1", "arg2", kwarg1="kwarg1", kwarg2=mock)

        @context.example
        def passes_without_spec(self):
            mock = unittest.mock.Mock()
            self.assert_passes(mock, "arg2", kwarg1="kwarg1", kwarg2="kwarg2")
            self.assert_passes("arg1", mock, kwarg1="kwarg1", kwarg2="kwarg2")
            self.assert_passes("arg1", "arg2", kwarg1=mock, kwarg2="kwarg2")
            self.assert_passes("arg1", "arg2", kwarg1="kwarg1", kwarg2=mock)

        @context.example
        def fails_with_invalid_spec(self):
            mock = unittest.mock.Mock(spec=int)
            self.assert_fails(mock, "arg2", kwarg1="kwarg1", kwarg2="kwarg2")
            self.assert_fails("arg1", mock, kwarg1="kwarg1", kwarg2="kwarg2")
            self.assert_fails("arg1", "arg2", kwarg1=mock, kwarg2="kwarg2")
            self.assert_fails("arg1", "arg2", kwarg1="kwarg1", kwarg2=mock)

    @context.sub_context("TypeVar")
    def typevar(context):
        @context.example
        def ingores_TypeVar(self):
            """
            We currently can't enforce TypeVar:
            https://github.com/facebookincubator/TestSlide/issues/165
            """

            def with_typevar(lolo: TypeVar("T")) -> None:
                pass

            self.callable_template = with_typevar
            self.assert_passes("arg1")
            self.assert_passes(kwarg1="arg1")

        @context.example
        def ignores_nested_TypeVar(self):
            """
            We currently can't enforce TypeVar:
            https://github.com/facebookincubator/TestSlide/issues/165
            """

            def with_typevar(arg1: Type[TypeVar("T")]) -> None:
                pass

            self.callable_template = with_typevar
            self.assert_passes("arg1")
            self.assert_passes(kwarg1="arg1")

    @context.sub_context
    def recursion_and_mocks(context):
        @context.sub_context("typing.Union")
        def typing_Union(context):
            @context.memoize
            def callable_template(self):
                return sample_module.test_union

            @context.example
            def passes_with_StritMock_without_template(self):
                self.assert_passes({"StrictMock": StrictMock()})

            @context.example("it works with unittest.mock.Mock without spec")
            def passes_with_unittest_mock_Mock_without_spec(self):
                self.assert_passes({"Mock": unittest.mock.Mock()})

            @context.example
            def passes_with_StritMock_with_valid_template(self):
                self.assert_passes(
                    {"StrictMock(template=str)": StrictMock(template=str)}
                )

            @context.example("passes with unittest.mock.Mock with valid spec")
            def passes_with_unittest_mock_Mock_with_valid_spec(self):
                self.assert_passes({"Mock(spec=str)": unittest.mock.Mock(spec=str)})

            @context.example
            def fails_with_StritMock_with_invalid_template(self):
                self.assert_fails(
                    {"StrictMock(template=dict)": StrictMock(template=dict)}
                )

            @context.example("fails with unittest.mock.Mock with invalid spec")
            def fails_with_unittest_mock_Mock_with_invalid_spec(self):
                self.assert_fails({"Mock(spec=dict)": unittest.mock.Mock(spec=dict)})

        @context.sub_context("typing.Tuple")
        def typing_Tuple(context):
            @context.memoize
            def callable_template(self):
                return sample_module.test_tuple

            @context.example
            def passes_with_StritMock_without_template(self):
                self.assert_passes({"StrictMock": ("str", StrictMock(),)})

            @context.example("it works with unittest.mock.Mock without spec")
            def passes_with_unittest_mock_Mock_without_spec(self):
                self.assert_passes({"Mock": ("str", unittest.mock.Mock(),)})

            @context.example
            def passes_with_StritMock_with_valid_template(self):
                self.assert_passes(
                    {"StrictMock(template=int)": ("str", StrictMock(template=int),)}
                )

            @context.example("passes with unittest.mock.Mock with valid spec")
            def passes_with_unittest_mock_Mock_with_valid_spec(self):
                self.assert_passes(
                    {"Mock(spec=int)": ("str", unittest.mock.Mock(spec=int),)}
                )

            @context.example
            def fails_with_StritMock_with_invalid_template(self):
                self.assert_fails(
                    {"StrictMock(template=dict)": ("str", StrictMock(template=dict),)}
                )

            @context.example("fails with unittest.mock.Mock with invalid spec")
            def fails_with_unittest_mock_Mock_with_invalid_spec(self):
                self.assert_fails(
                    {"Mock(spec=dict)": ("str", unittest.mock.Mock(spec=dict),)}
                )
