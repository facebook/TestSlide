# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import asyncio
import csv
import sys
import unittest

import testslide


class SomeClass:
    attribute = "value"

    @staticmethod
    def do_something():
        return "original"

    @staticmethod
    async def async_do_something():
        return "original"


class TestSlideTestCaseIntegration(testslide.TestCase):
    def test_inherits_from_unittest(self):
        self.assertTrue(issubclass(type(self), unittest.TestCase))

    def test_has_patch_attribute(self):
        self.patch_attribute(SomeClass, "attribute", "new_value")
        self.assertEqual(SomeClass.attribute, "new_value")

    def test_has_mock_callable(self):
        self.mock_callable(SomeClass, "do_something").to_return_value(
            42
        ).and_assert_called_once()
        self.assertEqual(SomeClass.do_something(), 42)

    def test_has_mock_async_callable(self):
        self.mock_async_callable(SomeClass, "async_do_something").to_return_value(
            42
        ).and_assert_called_once()
        if sys.version_info >= (3, 7):
            self.assertEqual(asyncio.run(SomeClass.async_do_something()), 42)
        else:
            loop = asyncio.get_event_loop()
            result = loop.run_until_complete(SomeClass.async_do_something())
            loop.close()
            self.assertEqual(result, 42)

    def test_has_mock_constructor(self):
        dict_reader = testslide.StrictMock(csv.DictReader)
        path = "/meh"
        self.mock_constructor(csv, "DictReader").for_call(path).to_return_value(
            dict_reader
        )
        self.assertTrue(id(dict_reader), id(csv.DictReader(path)))
