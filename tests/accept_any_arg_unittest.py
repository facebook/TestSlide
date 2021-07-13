from testslide import TestCase

from . import sample_module


class TestAcceptAnyArg(TestCase):
    def test_ignore_other_args(self):
        self.mock_callable(
            sample_module, "test_function", ignore_other_args=True
        ).for_call("a").to_return_value(["blah"])
        sample_module.test_function("a", "b")

    def test_ignore_other_kwargs(self):
        self.mock_callable(
            sample_module, "test_function", ignore_other_kwargs=True
        ).for_call("firstarg", "secondarg", kwarg1="a").to_return_value(["blah"])
        sample_module.test_function("firstarg", "secondarg", kwarg1="a", kwarg2="x")

    def test_ignore_other_args_and_kwargs(self):
        self.mock_callable(
            sample_module,
            "test_function",
            ignore_other_args=True,
            ignore_other_kwargs=True,
        ).for_call("firstarg", kwarg1="a").to_return_value(["blah"])
        sample_module.test_function("firstarg", "xx", kwarg1="a", kwarg2="x")
