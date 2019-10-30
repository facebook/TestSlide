# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import csv
import testslide
import unittest


class Dummy(object):
    def do_something(self):
        pass


class TestSlideTestCaseIntegration(testslide.TestCase):
    def test_inherits_from_unittest(self):
        self.assertTrue(issubclass(type(self), unittest.TestCase))

    def test_has_mock_callable(self):
        dummy = Dummy()
        self.mock_callable(dummy, "do_something").to_return_value(
            42
        ).and_assert_called_once()
        self.assertEqual(dummy.do_something(), 42)

    def test_has_mock_constructor(self):
        dict_reader = testslide.StrictMock(csv.DictReader)
        path = "/meh"
        self.mock_constructor(csv, "DictReader").for_call(path).to_return_value(
            dict_reader
        )
        self.assertTrue(id(dict_reader), id(csv.DictReader(path)))
