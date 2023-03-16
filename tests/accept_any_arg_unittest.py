# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from testslide import TestCase, matchers, mock_callable

from . import sample_module


class TestAcceptAnyArg(TestCase):
    def test_for_partial_call_accepts_all_other_args(self):
        self.mock_callable(sample_module, "test_function").for_partial_call(
            "a"
        ).to_return_value(["blah"])
        sample_module.test_function("a", "b")

    def test_for_partial_call_accepts_all_other_kwargs(self):
        self.mock_callable(sample_module, "test_function").for_partial_call(
            "firstarg", "secondarg", kwarg1="a"
        ).to_return_value(["blah"])
        sample_module.test_function("firstarg", "secondarg", kwarg1="a", kwarg2="x")

    def test_for_partial_call_accepts_all_other_args_and_kwargs(self):
        self.mock_callable(
            sample_module,
            "test_function",
        ).for_partial_call(
            "firstarg", kwarg1="a"
        ).to_return_value(["blah"])
        sample_module.test_function("firstarg", "xx", kwarg1="a", kwarg2="x")

    def test_for_partial_call_fails_if_no_required_args_are_present(self):
        with self.assertRaises(mock_callable.UnexpectedCallArguments):
            self.mock_callable(
                sample_module,
                "test_function",
            ).for_partial_call(
                "firstarg", kwarg1="a"
            ).to_return_value(["blah"])
            sample_module.test_function(
                "differentarg", "alsodifferent", kwarg1="a", kwarg2="x"
            )

    def test_for_partial_call_fails_if_no_required_kwargs_are_present(self):
        with self.assertRaises(mock_callable.UnexpectedCallArguments):
            self.mock_callable(
                sample_module,
                "test_function",
            ).for_partial_call(
                "firstarg", kwarg1="x"
            ).to_return_value(["blah"])
            sample_module.test_function("firstarg", "secondarg", kwarg1="a", kwarg2="x")

    def test_matchers_work_with_for_partial_call(self):
        self.mock_callable(
            sample_module,
            "test_function",
        ).for_partial_call(
            matchers.Any(), "secondarg"
        ).to_return_value(["blah"])
        sample_module.test_function("asdasdeas", "secondarg", kwarg1="a", kwarg2="x")
