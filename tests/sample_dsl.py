from testslide.dsl import context
import unittest
import os
import sys


class SimulatedFailure(Exception):
    def __init__(self, message, second_message):
        """
        This method purposely accepts an extra argument to catch failures when
        reraising exceptions.
        """
        super(SimulatedFailure, self).__init__(message, second_message)
        self.message = message
        self.second_message = second_message

    def __str__(self):
        return "{} {}".format(self.message, self.second_message)


def _cond_print(name):
    if "PRINT" in os.environ:
        print(f"{name} stdout")
        print(f"{name} stderr", file=sys.stderr)


@context
def top_context(context):
    @context.example
    def passing_example(self):
        _cond_print("passing_example")

    @context.example
    def failing_example(self):
        _cond_print("failing_example")
        raise SimulatedFailure("test failure", "(extra)")

    @context.fexample
    def focused_example(self):
        _cond_print("focused_example")

    @context.xexample
    def skipped_example(self):
        _cond_print("skipped_example")

    @context.example
    def unittest_SkipTest(self):
        _cond_print("unittest_SkipTest")
        raise unittest.SkipTest("Skipped with unittest.SkipTest")

    @context.sub_context
    def nested_context(context):
        @context.example
        def passing_nested_example(self):
            _cond_print("passing_nested_example")
