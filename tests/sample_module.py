# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from typing import Dict, Optional, Tuple, Union

attribute = "value"


class OtherClass:
    pass


class SomeClass:
    attribute = "value"
    _private_attr = "sooprivate"
    other_class_attribute = OtherClass

    def method(self):
        pass

    @property
    def property_attribute(self):
        return "property_attribute"

    def instance_method_with_star_args(
        self, first, *args: str, a: bool, b: int, c: Optional[int], d: int = 3
    ) -> int:
        return 3


class TargetStr(object):
    def __str__(self):
        return "original response"

    def _privatefun(self):
        return "cannotbemocked"


class ParentTarget(TargetStr):
    def instance_method(
        self, arg1: str, arg2: str, kwarg1: str = "", kwarg2: str = ""
    ) -> str:
        return "original response"

    async def async_instance_method(
        self, arg1: str, arg2: str, kwarg1: str = "", kwarg2: str = ""
    ) -> str:
        return "async original response"

    @staticmethod
    def static_method(arg1: str, arg2: str, kwarg1: str = "", kwarg2: str = "") -> str:
        return "original response"

    @staticmethod
    async def async_static_method(
        arg1: str, arg2: str, kwarg1: str = "", kwarg2: str = ""
    ) -> str:
        return "async original response"

    @classmethod
    def class_method(
        cls, arg1: str, arg2: str, kwarg1: str = "", kwarg2: str = ""
    ) -> str:
        return "original response"

    @classmethod
    async def async_class_method(
        cls, arg1: str, arg2: str, kwarg1: str = "", kwarg2: str = ""
    ) -> str:
        return "async original response"

    async def __aiter__(self):
        return self


class Target(ParentTarget):
    def __init__(self):
        self.dynamic_instance_method = (
            lambda arg1, arg2, kwarg1=None, kwarg2=None: "original response"
        )
        super(Target, self).__init__()

    @property
    def invalid(self):
        """
        Covers a case where create_autospec at an instance would fail.
        """
        raise RuntimeError("Should not be accessed")


class CallOrderTarget(object):
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return self.name

    def f1(self, arg):
        return "f1: {}".format(repr(arg))

    def f2(self, arg):
        return "f2: {}".format(repr(arg))


def test_function(arg1: str, arg2: str, kwarg1: str = "", kwarg2: str = "") -> str:
    "This function is used by some unit tests only"
    return "original response"


async def async_test_function(
    arg1: str, arg2: str, kwarg1: str = "", kwarg2: str = ""
) -> str:
    "This function is used by some unit tests only"
    return "original response"


UnionArgType = Dict[str, Union[str, int]]


def test_union(arg: UnionArgType):
    pass


TupleArgType = Dict[str, Tuple[str, int]]


def test_tuple(arg: TupleArgType):
    pass
