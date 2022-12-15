# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import sys

import testslide


class QuestBase:
    def __init_subclass__(cls, swallow, **kwargs):
        cls.swallow = swallow
        super().__init_subclass__(**kwargs)


class Quest(QuestBase, swallow="african"):
    pass


class TestPEP487(testslide.TestCase):
    def setUp(self):
        super().setUp()
        self.q0mock = testslide.StrictMock(template=Quest)
        self.mock_constructor(
            sys.modules[__name__], "Quest", swallow="barn"
        ).to_return_value(self.q0mock)
        self.q0mock.swallow = "barn"

    def test_pep487_q0(self):
        quest = Quest()
        self.assertEqual(quest.swallow, "barn")
