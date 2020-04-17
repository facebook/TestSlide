# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from typing import Type, TypeVar
from testslide.dsl import context, xcontext, fcontext, Skip  # noqa: F401
import testslide.lib
from . import sample_module
from testslide import StrictMock
import unittest.mock


@context("_validate_function_signature")
def _validate_function_signature(context):
    @context.sub_context
    def valid_types(context):
        @context.function
        def assert_passes(self, *args, **kwargs):
            testslide.lib._validate_function_signature(
                sample_module.test_function, args, kwargs
            )

        @context.example
        def canonical(self):
            self.assert_passes("arg1", "arg2", kwarg1="kwarg1", kwarg2="kwarg2")

        @context.example
        def kwargs_as_args(self):
            self.assert_passes("arg1", "arg2", "kwarg1", "kwarg2")
            self.assert_passes("arg1", "arg2", "kwarg1", kwarg2="kwarg2")

        @context.example
        def args_as_kwargs(self):
            self.assert_passes("arg1", arg2="arg2", kwarg1="kwarg1", kwarg2="kwarg2")
            self.assert_passes(
                arg1="arg1", arg2="arg2", kwarg1="kwarg1", kwarg2="kwarg2"
            )

        @context.example
        def varargs_and_varkwargs(self):
            testslide.lib._validate_function_signature(
                object.__new__, (1, 2, 3), {"four": 5, "six": 6}
            )

        @context.example("testslide.StrictMock with valid template")
        def testslide_StrictMock_with_valid_template(self):
            strict_mock = StrictMock(template=str)
            self.assert_passes(strict_mock, "arg2", kwarg1="kwarg1", kwarg2="kwarg2")
            self.assert_passes("arg1", strict_mock, kwarg1="kwarg1", kwarg2="kwarg2")
            self.assert_passes("arg1", "arg2", kwarg1=strict_mock, kwarg2="kwarg2")
            self.assert_passes("arg1", "arg2", kwarg1="kwarg1", kwarg2=strict_mock)

        @context.example("testslide.StrictMock without template")
        def testslide_StrictMock_without_template(self):
            strict_mock = StrictMock()
            self.assert_passes(strict_mock, "arg2", kwarg1="kwarg1", kwarg2="kwarg2")
            self.assert_passes("arg1", strict_mock, kwarg1="kwarg1", kwarg2="kwarg2")
            self.assert_passes("arg1", "arg2", kwarg1=strict_mock, kwarg2="kwarg2")
            self.assert_passes("arg1", "arg2", kwarg1="kwarg1", kwarg2=strict_mock)

        @context.example("unittest.mock.Mock with valid spec")
        def unittest_mock_Mock_with_valid_spec(self):
            mock = unittest.mock.Mock(spec=str)
            self.assert_passes(mock, "arg2", kwarg1="kwarg1", kwarg2="kwarg2")
            self.assert_passes("arg1", mock, kwarg1="kwarg1", kwarg2="kwarg2")
            self.assert_passes("arg1", "arg2", kwarg1=mock, kwarg2="kwarg2")
            self.assert_passes("arg1", "arg2", kwarg1="kwarg1", kwarg2=mock)

        @context.example("unittest.mock.Mock without spec")
        def unittest_mock_Mock_without_spec(self):
            mock = unittest.mock.Mock()
            self.assert_passes(mock, "arg2", kwarg1="kwarg1", kwarg2="kwarg2")
            self.assert_passes("arg1", mock, kwarg1="kwarg1", kwarg2="kwarg2")
            self.assert_passes("arg1", "arg2", kwarg1=mock, kwarg2="kwarg2")
            self.assert_passes("arg1", "arg2", kwarg1="kwarg1", kwarg2=mock)

        @context.example("TypeVar")
        def typevar(self):
            """We currently can't enforce typevars"""

            def with_typevar(lolo: TypeVar("T")) -> None:
                pass

            testslide.lib._validate_function_signature(
                with_typevar, args=["arg1"], kwargs={}
            )
            testslide.lib._validate_function_signature(
                with_typevar, args=[], kwargs={"arg1": "arg1"}
            )

        @context.example("Nested TypeVar")
        def nested_typevar(self):
            """We currently can't enforce typevars"""

            def with_typevar(arg1: Type[TypeVar("T")]) -> None:
                pass

            testslide.lib._validate_function_signature(
                with_typevar, args=["arg1"], kwargs={}
            )
            testslide.lib._validate_function_signature(
                with_typevar, args=[], kwargs={"arg1": "arg1"}
            )

    @context.sub_context
    def invalid_types(context):
        @context.function
        def assert_fails(self, *args, **kwargs):
            with self.assertRaisesRegex(
                TypeError, "Call with incompatible argument types"
            ):
                testslide.lib._validate_function_signature(
                    sample_module.test_function, args, kwargs
                )

        @context.example
        def error_message(self):
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
                testslide.lib._validate_function_signature(
                    sample_module.test_function, (1, 2, 3, 4), {}
                )

        @context.example
        def canonical(self):
            self.assert_fails(1, "arg2", kwarg1="kwarg1", kwarg2="kwarg2")
            self.assert_fails("arg1", 2, kwarg1="kwarg1", kwarg2="kwarg2")
            self.assert_fails("arg1", "arg2", kwarg1=1, kwarg2="kwarg2")
            self.assert_fails("arg1", "arg2", kwarg1="kwarg1", kwarg2=2)

        @context.example
        def kwargs_as_args(self):
            self.assert_fails("arg1", "arg2", 1, "kwarg2")
            self.assert_fails("arg1", "arg2", "kwarg1", 2)
            self.assert_fails("arg1", "arg2", 1, kwarg2="kwarg2")
            self.assert_fails("arg1", "arg2", "kwargs1", kwarg2=2)

        @context.example
        def args_as_kwargs(self):
            self.assert_fails(arg1=1, arg2="arg2", kwarg1="kwarg1", kwarg2="kwarg2")
            self.assert_fails(arg1="arg1", arg2=2, kwarg1="kwarg1", kwarg2="kwarg2")
            self.assert_fails(arg1="arg1", arg2="arg2", kwarg1=1, kwarg2="kwarg2")
            self.assert_fails(arg1="arg1", arg2="arg2", kwarg1="kwarg1", kwarg2=2)

        @context.example("testslide.StrictMock with invalid template")
        def testslide_StrictMock_with_invalid_template(self):
            strict_mock = StrictMock(template=int)
            self.assert_fails(strict_mock, "arg2", kwarg1="kwarg1", kwarg2="kwarg2")
            self.assert_fails("arg1", strict_mock, kwarg1="kwarg1", kwarg2="kwarg2")
            self.assert_fails("arg1", "arg2", kwarg1=strict_mock, kwarg2="kwarg2")
            self.assert_fails("arg1", "arg2", kwarg1="kwarg1", kwarg2=strict_mock)

        @context.example("unittest.mock.Mock with valid spec")
        def unittest_mock_Mock_with_valid_spec(self):
            mock = unittest.mock.Mock(spec=int)
            self.assert_fails(mock, "arg2", kwarg1="kwarg1", kwarg2="kwarg2")
            self.assert_fails("arg1", mock, kwarg1="kwarg1", kwarg2="kwarg2")
            self.assert_fails("arg1", "arg2", kwarg1=mock, kwarg2="kwarg2")
            self.assert_fails("arg1", "arg2", kwarg1="kwarg1", kwarg2=mock)
