# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import unittest

from testslide.core.strict_mock import StrictMock


class Template:
    def method(self) -> str:
        return "template"

    def __len__(self) -> int:
        return 0


class StrictMockSubclass(StrictMock):
    def __init__(self) -> None:
        super().__init__(template=Template)

    def method(self) -> str:
        self.__return_value = "mock"
        return self.__return_value

    def __len__(self) -> int:
        return 100


class StrictMockSubclassTest(unittest.TestCase):
    def test_overrides_regular_and_magic_methods(self) -> None:
        strict_mock = StrictMockSubclass()

        self.assertEqual(strict_mock.method(), "mock")
        self.assertEqual(len(strict_mock), 100)
