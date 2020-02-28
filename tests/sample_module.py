# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

attribute = "value"


class OtherClass:
    pass


class SomeClass:
    attribute = "value"
    other_class_attribute = OtherClass

    def method(self):
        pass


def test_function(arg1, arg2, kwarg1=None, kwarg2=None):
    "This function is used by some unit tests only"
    return "original response"


async def async_test_function(arg1, arg2, kwarg1=None, kwarg2=None):
    "This function is used by some unit tests only"
    return "original response"
