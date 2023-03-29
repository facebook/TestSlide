# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from collections import deque

import testslide

from . import sample_module


class IntMatcherTest(testslide.TestCase):
    def testAnyInt(self):
        self.assertEqual(testslide.matchers.AnyInt(), 666)
        self.assertEqual(testslide.matchers.AnyInt(), 42)
        self.assertNotEqual(testslide.matchers.AnyInt(), "derp")

    def test_NotThisInt(self):
        self.assertEqual(testslide.matchers.NotThisInt(666), 42)
        self.assertNotEqual(testslide.matchers.NotThisInt(69), 69)
        self.assertNotEqual(testslide.matchers.NotThisInt(42), "derp")
        with self.assertRaises(ValueError):
            testslide.matchers.NotThisInt("derp")
        with self.assertRaises(ValueError):
            testslide.matchers.NotThisInt(1.340)

    def test_IntBetween(self):
        self.assertEqual(testslide.matchers.IntBetween(21, 666), 42)
        self.assertEqual(testslide.matchers.IntBetween(21, 666), 21)
        self.assertEqual(testslide.matchers.IntBetween(21, 666), 666)
        self.assertNotEqual(testslide.matchers.IntBetween(42, 69), 666)
        self.assertNotEqual(testslide.matchers.IntBetween(42, 69), "derp")
        with self.assertRaises(ValueError):
            testslide.matchers.IntBetween("derp", 42)
        with self.assertRaises(ValueError):
            testslide.matchers.IntBetween(42.42, "derp")
        with self.assertRaises(ValueError):
            testslide.matchers.IntBetween("derp", "derp")

    def test_IntGreaterThan(self):
        self.assertEqual(testslide.matchers.IntGreaterThan(21), 42)
        self.assertNotEqual(testslide.matchers.IntGreaterThan(21), 21)
        self.assertNotEqual(testslide.matchers.IntGreaterThan(21), 20)
        self.assertNotEqual(testslide.matchers.IntGreaterThan(42), "derp")
        with self.assertRaises(ValueError):
            testslide.matchers.IntGreaterThan("derp")

    def test_IntGreaterOrEquals(self):
        self.assertEqual(testslide.matchers.IntGreaterOrEquals(21), 42)
        self.assertEqual(testslide.matchers.IntGreaterOrEquals(21), 21)
        self.assertNotEqual(testslide.matchers.IntGreaterOrEquals(21), 20)
        self.assertNotEqual(testslide.matchers.IntGreaterOrEquals(42), "derp")
        with self.assertRaises(ValueError):
            testslide.matchers.IntGreaterOrEquals("derp")

    def test_IntLessThan(self):
        self.assertEqual(testslide.matchers.IntLessThan(21), 20)
        self.assertNotEqual(testslide.matchers.IntLessThan(21), 21)
        self.assertNotEqual(testslide.matchers.IntLessThan(21), 22)
        self.assertNotEqual(testslide.matchers.IntLessThan(42), "derp")
        with self.assertRaises(ValueError):
            testslide.matchers.IntLessThan("derp")

    def test_IntLessOrEquals(self):
        self.assertEqual(testslide.matchers.IntLessOrEquals(21), 20)
        self.assertEqual(testslide.matchers.IntLessOrEquals(21), 21)
        self.assertNotEqual(testslide.matchers.IntLessOrEquals(21), 22)
        self.assertNotEqual(testslide.matchers.IntLessOrEquals(42), "derp")
        with self.assertRaises(ValueError):
            testslide.matchers.IntLessOrEquals("derp")


class FloatMatcherTest(testslide.TestCase):
    def test_NotThisFloat(self):
        self.assertEqual(testslide.matchers.NotThisFloat(66.6), 4.2)
        self.assertNotEqual(testslide.matchers.NotThisFloat(6.9), 6.9)
        self.assertNotEqual(testslide.matchers.NotThisFloat(4.2), "derp")
        with self.assertRaises(ValueError):
            testslide.matchers.NotThisFloat("derp")
        with self.assertRaises(ValueError):
            testslide.matchers.NotThisFloat(10)

    def test_FloatBetween(self):
        self.assertEqual(testslide.matchers.FloatBetween(2.1, 666), 4.2)
        self.assertEqual(testslide.matchers.FloatBetween(2.1, 666), 2.1)
        self.assertEqual(testslide.matchers.FloatBetween(21, 66.6), 66.6)
        self.assertNotEqual(testslide.matchers.FloatBetween(4.2, 6.9), 66.6)
        self.assertNotEqual(testslide.matchers.FloatBetween(4.2, 6.9), "derp")
        with self.assertRaises(ValueError):
            testslide.matchers.FloatBetween("derp", 42.0)
        with self.assertRaises(ValueError):
            testslide.matchers.FloatBetween(42, "derp")
        with self.assertRaises(ValueError):
            testslide.matchers.FloatBetween("derp", "derp")

    def test_FloatGreaterThan(self):
        self.assertEqual(testslide.matchers.FloatGreaterThan(2.1), 4.2)
        self.assertNotEqual(testslide.matchers.FloatGreaterThan(2.1), 2.1)
        self.assertNotEqual(testslide.matchers.FloatGreaterThan(2.1), 2.0)
        self.assertNotEqual(testslide.matchers.FloatGreaterThan(4.2), "derp")
        with self.assertRaises(ValueError):
            testslide.matchers.FloatGreaterThan("derp")

    def test_FloatGreaterOrEquals(self):
        self.assertEqual(testslide.matchers.FloatGreaterOrEquals(2.1), 4.2)
        self.assertEqual(testslide.matchers.FloatGreaterOrEquals(2.1), 2.1)
        self.assertNotEqual(testslide.matchers.FloatGreaterOrEquals(2.1), 2.0)
        self.assertNotEqual(testslide.matchers.FloatGreaterOrEquals(4.2), "derp")
        with self.assertRaises(ValueError):
            testslide.matchers.FloatGreaterOrEquals("derp")

    def test_FloatLessThan(self):
        self.assertEqual(testslide.matchers.FloatLessThan(2.1), 2.0)
        self.assertNotEqual(testslide.matchers.FloatLessThan(2.1), 2.1)
        self.assertNotEqual(testslide.matchers.FloatLessThan(2.1), 2.2)
        self.assertNotEqual(testslide.matchers.FloatLessThan(4.2), "derp")
        with self.assertRaises(ValueError):
            testslide.matchers.FloatLessThan("derp")

    def test_FloatLessOrEquals(self):
        self.assertEqual(testslide.matchers.FloatLessOrEquals(2.1), 2.0)
        self.assertEqual(testslide.matchers.FloatLessOrEquals(2.1), 2.1)
        self.assertNotEqual(testslide.matchers.FloatLessOrEquals(2.1), 2.2)
        self.assertNotEqual(testslide.matchers.FloatLessOrEquals(4.2), "derp")
        with self.assertRaises(ValueError):
            testslide.matchers.FloatLessOrEquals("derp")


class GenericTestCase(testslide.TestCase):
    def testAnyFalsey(self):
        self.assertEqual(testslide.matchers.AnyFalsey(), {})
        self.assertEqual(testslide.matchers.AnyFalsey(), [])
        self.assertEqual(testslide.matchers.AnyFalsey(), ())
        self.assertEqual(testslide.matchers.AnyFalsey(), "")
        self.assertEqual(testslide.matchers.AnyFalsey(), None)
        self.assertEqual(testslide.matchers.AnyFalsey(), 0)
        self.assertNotEqual(testslide.matchers.AnyFalsey(), {"a": "b"})
        self.assertNotEqual(testslide.matchers.AnyFalsey(), ["a", "b"])
        self.assertNotEqual(testslide.matchers.AnyFalsey(), ("a", "b"))
        self.assertNotEqual(testslide.matchers.AnyFalsey(), "a")
        self.assertNotEqual(testslide.matchers.AnyFalsey(), 1)

    def testAnyTruthy(self):
        self.assertNotEqual(testslide.matchers.AnyTruthy(), {})
        self.assertNotEqual(testslide.matchers.AnyTruthy(), [])
        self.assertNotEqual(testslide.matchers.AnyTruthy(), ())
        self.assertNotEqual(testslide.matchers.AnyTruthy(), "")
        self.assertNotEqual(testslide.matchers.AnyTruthy(), None)
        self.assertNotEqual(testslide.matchers.AnyTruthy(), 0)
        self.assertEqual(testslide.matchers.AnyTruthy(), {"a": "b"})
        self.assertEqual(testslide.matchers.AnyTruthy(), ["a", "b"])
        self.assertEqual(testslide.matchers.AnyTruthy(), ("a", "b"))
        self.assertEqual(testslide.matchers.AnyTruthy(), "a")
        self.assertEqual(testslide.matchers.AnyTruthy(), 1)

    def testAny(self):
        self.assertEqual(testslide.matchers.Any(), {})
        self.assertEqual(testslide.matchers.Any(), [])
        self.assertEqual(testslide.matchers.Any(), ())
        self.assertEqual(testslide.matchers.Any(), "")
        self.assertEqual(testslide.matchers.Any(), None)
        self.assertEqual(testslide.matchers.Any(), 0)
        self.assertEqual(testslide.matchers.Any(), {"a": "b"})
        self.assertEqual(testslide.matchers.Any(), ["a", "b"])
        self.assertEqual(testslide.matchers.Any(), ("a", "b"))
        self.assertEqual(testslide.matchers.Any(), "a")
        self.assertEqual(testslide.matchers.Any(), 1)

    def testAnyInstanceOf(self):
        self.assertEqual(testslide.matchers.AnyInstanceOf(str), "durrdurr")
        self.assertNotEqual(testslide.matchers.AnyInstanceOf(str), 7)
        with self.assertRaises(ValueError):
            testslide.matchers.AnyInstanceOf(2)

    def testAnyWithCall(self):
        self.assertEqual(testslide.matchers.AnyWithCall(lambda x: "b" in x), "abc")
        self.assertNotEqual(testslide.matchers.AnyWithCall(lambda x: "d" in x), "abc")


class StringTest(testslide.TestCase):
    def testAnyStr(self):
        self.assertEqual(testslide.matchers.AnyStr(), "aa")
        self.assertEqual(testslide.matchers.AnyStr(), "")
        self.assertNotEqual(testslide.matchers.AnyStr(), 69)
        self.assertNotEqual(testslide.matchers.AnyStr(), None)

    def testRegexMatches(self):
        self.assertEqual(testslide.matchers.RegexMatches("b[aeiou]t"), "bott")
        self.assertNotEqual(testslide.matchers.RegexMatches("b[aeiou]t"), "boot")
        self.assertNotEqual(testslide.matchers.RegexMatches("b[aeiou]t"), 13)

    def testStrContaining(self):
        self.assertEqual(testslide.matchers.StrContaining("bot"), "bott")
        self.assertNotEqual(testslide.matchers.StrContaining("derp"), "boot")
        self.assertNotEqual(testslide.matchers.StrContaining("derp"), 13)
        with self.assertRaises(ValueError):
            testslide.matchers.StrContaining(10)
        with self.assertRaises(ValueError):
            testslide.matchers.StrContaining(10.0)

    def testStrStartingWith(self):
        self.assertEqual(testslide.matchers.StrStartingWith("bo"), "bott")
        self.assertNotEqual(testslide.matchers.StrStartingWith("derp"), "boot")
        self.assertNotEqual(testslide.matchers.StrStartingWith("derp"), 13)
        with self.assertRaises(ValueError):
            testslide.matchers.StrStartingWith(10)
        with self.assertRaises(ValueError):
            testslide.matchers.StrStartingWith(10.0)

    def testStrEndingWith(self):
        self.assertEqual(testslide.matchers.StrEndingWith("ott"), "bott")
        self.assertNotEqual(testslide.matchers.StrEndingWith("derp"), "boot")
        self.assertNotEqual(testslide.matchers.StrEndingWith("derp"), 13)
        with self.assertRaises(ValueError):
            testslide.matchers.StrEndingWith(10)
        with self.assertRaises(ValueError):
            testslide.matchers.StrEndingWith(10.0)


class TestLists(testslide.TestCase):
    def testAnyList(self):
        self.assertEqual(testslide.matchers.AnyList(), [])
        self.assertEqual(testslide.matchers.AnyList(), [69, 42, "derp"])
        self.assertNotEqual(testslide.matchers.AnyList(), 69)
        self.assertNotEqual(testslide.matchers.AnyList(), None)

    def testListContainingElement(self):
        self.assertEqual(testslide.matchers.ListContaining(1), [1, 2, 3])
        self.assertNotEqual(testslide.matchers.ListContaining(1), [2, 3, 4])
        self.assertNotEqual(testslide.matchers.ListContaining(1), "DERP")

    def testListContainingAll(self):
        self.assertEqual(testslide.matchers.ListContainingAll([1, 2]), [1, 2, 3])
        self.assertNotEqual(
            testslide.matchers.ListContainingAll([1, 2, 3, 5]), [2, 3, 4]
        )
        self.assertNotEqual(testslide.matchers.ListContainingAll([1, 2, 3, 5]), "DERP")
        with self.assertRaises(ValueError):
            testslide.matchers.ListContainingAll({"a": "aa", "b": "bb"})
        with self.assertRaises(ValueError):
            testslide.matchers.ListContainingAll("derp")
        with self.assertRaises(ValueError):
            testslide.matchers.ListContainingAll(10)


class TestDicts(testslide.TestCase):
    def testAnyDict(self):
        self.assertEqual(testslide.matchers.AnyDict(), {})
        self.assertEqual(testslide.matchers.AnyDict(), {"a": 1})
        self.assertNotEqual(testslide.matchers.AnyDict(), 69)
        self.assertNotEqual(testslide.matchers.AnyDict(), [])
        self.assertNotEqual(testslide.matchers.AnyDict(), None)

    def testNotEmptyDict(self):
        self.assertEqual(testslide.matchers.NotEmptyDict(), {"a": 1})
        self.assertNotEqual(testslide.matchers.NotEmptyDict(), {})
        self.assertNotEqual(testslide.matchers.NotEmptyDict(), 69)
        self.assertNotEqual(testslide.matchers.NotEmptyDict(), [])
        self.assertNotEqual(testslide.matchers.NotEmptyDict(), None)

    def testEmptyDict(self):
        self.assertNotEqual(testslide.matchers.EmptyDict(), {"a": 1})
        self.assertEqual(testslide.matchers.EmptyDict(), {})
        self.assertNotEqual(testslide.matchers.EmptyDict(), 69)
        self.assertNotEqual(testslide.matchers.EmptyDict(), [])
        self.assertNotEqual(testslide.matchers.EmptyDict(), None)

    def testDictSupersetOf(self):
        self.assertEqual(
            testslide.matchers.DictSupersetOf({"a": "b", "c": 1}),
            {"a": "b", "c": 1, "d": "e"},
        )
        self.assertNotEqual(
            testslide.matchers.DictSupersetOf({"a": "b", "c": 1}), {"c": 1, "d": "e"}
        )
        self.assertNotEqual(testslide.matchers.DictSupersetOf({}), "DERP")
        with self.assertRaises(ValueError):
            testslide.matchers.DictSupersetOf(10)
        with self.assertRaises(ValueError):
            testslide.matchers.DictSupersetOf("derp")
        with self.assertRaises(ValueError):
            testslide.matchers.DictSupersetOf(["a", "b", "c"])

    def testDictContainingKeys(self):
        self.assertEqual(
            testslide.matchers.DictContainingKeys(["a", "c"]),
            {"a": "b", "c": 1, "d": "e"},
        )
        self.assertNotEqual(
            testslide.matchers.DictContainingKeys(["a", "b", "c"]), {"c": 1, "d": "e"}
        )
        self.assertNotEqual(testslide.matchers.DictContainingKeys([1, 2]), "DERP")
        with self.assertRaises(ValueError):
            testslide.matchers.DictContainingKeys(10)
        with self.assertRaises(ValueError):
            testslide.matchers.DictContainingKeys("derp")
        with self.assertRaises(ValueError):
            testslide.matchers.DictContainingKeys({"a", "b", "c"})


class TestIterable(testslide.TestCase):
    def testAnyContaining(self):
        # list
        self.assertEqual(testslide.matchers.AnyContaining(1), [1, 2, 3])
        self.assertNotEqual(testslide.matchers.AnyContaining(1), [2, 3, 4])
        # non-list collection
        self.assertEqual(
            testslide.matchers.AnyContaining(1), deque([1, 2, 3], maxlen=100)
        )
        self.assertEqual(
            testslide.matchers.AnyContaining(1), deque([1, 2, 3], maxlen=100)
        )
        # string
        with self.assertRaises(TypeError):
            self.assertNotEqual(testslide.matchers.AnyContaining(1), "DERP")
        self.assertEqual(testslide.matchers.AnyContaining("E"), "DERP")
        self.assertNotEqual(testslide.matchers.AnyContaining("A"), "DERP")

    def testAnyContainingAll(self):
        # list
        self.assertEqual(testslide.matchers.AnyContainingAll([1, 2]), [1, 2, 3])
        self.assertNotEqual(
            testslide.matchers.AnyContainingAll([1, 2, 3, 5]), [2, 3, 4]
        )
        # non-list
        self.assertEqual(testslide.matchers.AnyContainingAll([1, 2]), {1, 2, 3})
        self.assertNotEqual(
            testslide.matchers.AnyContainingAll([1, 2, 3, 5]), {2, 3, 4}
        )
        self.assertEqual(testslide.matchers.AnyContainingAll({1, 2}), [1, 2, 3])
        self.assertNotEqual(
            testslide.matchers.AnyContainingAll({1, 2, 3, 5}), [2, 3, 4]
        )
        # non-iterables
        with self.assertRaises(TypeError):
            self.assertEqual(testslide.matchers.AnyContainingAll(10), [1, 2, 3])
        with self.assertRaises(TypeError):
            self.assertEqual(testslide.matchers.AnyContainingAll([1, 2, 3]), 10)

    def testAnyIterable(self):
        self.assertEqual(testslide.matchers.AnyIterable(), [1, 2, 3])
        self.assertEqual(testslide.matchers.AnyIterable(), range(3))
        self.assertEqual(testslide.matchers.AnyIterable(), {1, 2, 3})
        self.assertNotEqual(testslide.matchers.AnyIterable(), 10)

    def testIterableWithElements(self):
        self.assertEqual(testslide.matchers.IterableWithElements([1, 2, 3]), [1, 2, 3])
        # subset
        self.assertNotEqual(testslide.matchers.IterableWithElements([1, 2]), [1, 2, 3])
        # non-list
        self.assertEqual(
            testslide.matchers.IterableWithElements([1, 2, 3]),
            deque([1, 2, 3], maxlen=100),
        )
        self.assertNotEqual(
            testslide.matchers.IterableWithElements([2, 3, 4]),
            deque([1, 2, 3], maxlen=100),
        )
        self.assertEqual(
            testslide.matchers.IterableWithElements(range(1, 4)),
            [1, 2, 3],
        )

    def testExhaustedIterators(self):
        expected_list = [1, 2, 3]
        for MatcherClass in (
            testslide.matchers.AnyContainingAll,
            testslide.matchers.IterableWithElements,
        ):
            it = iter(expected_list)
            matcher = MatcherClass(it)

            # verify iterator is exhausted
            with self.assertRaises(StopIteration):
                next(it)

            self.assertEqual(
                matcher,
                expected_list,
            )
            # Asserting against this matcher twice produces the same result
            self.assertEqual(
                matcher,
                expected_list,
            )

    def testAnyEmpty(self):
        # Sized
        self.assertEqual(testslide.matchers.AnyEmpty(), [])
        self.assertEqual(testslide.matchers.AnyEmpty(), {})
        self.assertNotEqual(testslide.matchers.AnyEmpty(), [1, 2, 3])
        # iterables without len()
        with self.assertRaises(TypeError):
            self.assertEqual(testslide.matchers.AnyEmpty(), iter([]))
        with self.assertRaises(TypeError):
            self.assertNotEqual(testslide.matchers.AnyEmpty(), iter([1, 2, 3]))
        with self.assertRaises(TypeError):
            self.assertEqual(testslide.matchers.AnyEmpty(), 10)

    def testAnyNotEmpty(self):
        # Sized
        self.assertNotEqual(testslide.matchers.AnyNotEmpty(), [])
        self.assertEqual(testslide.matchers.AnyNotEmpty(), [1, 2, 3])
        self.assertEqual(testslide.matchers.AnyNotEmpty(), {1, 2, 3})
        # iterables without len()
        with self.assertRaises(TypeError):
            self.assertNotEqual(testslide.matchers.AnyNotEmpty(), iter([]))
        with self.assertRaises(TypeError):
            self.assertEqual(testslide.matchers.AnyNotEmpty(), iter([1, 2, 3]))
        # not iterable
        with self.assertRaises(TypeError):
            self.assertEqual(testslide.matchers.AnyNotEmpty(), 10)


class TestChaining(testslide.TestCase):
    def testBitwiseAnd(self):
        self.assertTrue(
            isinstance(
                testslide.matchers.Any() & testslide.matchers.AnyStr(),
                testslide.matchers._AndMatcher,
            )
        )
        self.assertEqual(testslide.matchers.Any() & testslide.matchers.AnyStr(), "a")
        self.assertNotEqual(testslide.matchers.Any() & testslide.matchers.AnyStr(), 3)

    def testBitwiseOr(self):
        self.assertTrue(
            isinstance(
                testslide.matchers.Any() | testslide.matchers.AnyStr(),
                testslide.matchers._OrMatcher,
            )
        )
        self.assertEqual(testslide.matchers.AnyInt() | testslide.matchers.AnyStr(), "a")
        self.assertEqual(testslide.matchers.AnyInt() | testslide.matchers.AnyStr(), 3)
        self.assertNotEqual(
            testslide.matchers.AnyInt() | testslide.matchers.AnyStr(), []
        )

    def testBitwiseXor(self):
        self.assertTrue(
            isinstance(
                testslide.matchers.Any() ^ testslide.matchers.AnyStr(),
                testslide.matchers._XorMatcher,
            )
        )
        self.assertEqual(testslide.matchers.AnyInt() ^ testslide.matchers.AnyStr(), [])
        self.assertNotEqual(
            testslide.matchers.AnyInt() ^ testslide.matchers.AnyStr(), 3
        )

    def testBitwiseInverse(self):
        inverted_matcher = ~testslide.matchers.StrContaining("Fabio")
        self.assertTrue(isinstance(inverted_matcher, testslide.matchers._InvMatcher))
        self.assertEqual(inverted_matcher, "Balint")
        self.assertNotEqual(inverted_matcher, "Fabio.")

    def testCannotChainMoreThanTwo(self):
        with self.assertRaises(testslide.matchers.AlreadyChainedException):
            testslide.matchers.Any() | testslide.matchers.AnyStr() | testslide.matchers.AnyInt()
        with self.assertRaises(testslide.matchers.AlreadyChainedException):
            (
                testslide.matchers.Any()
                & testslide.matchers.AnyStr()
                & testslide.matchers.AnyInt()
            )
        with self.assertRaises(testslide.matchers.AlreadyChainedException):
            (
                testslide.matchers.Any()
                ^ testslide.matchers.AnyStr()
                ^ testslide.matchers.AnyInt()
            )


class TestUsageWithPatchCallable(testslide.TestCase):
    def test_patch_callable(self):
        self.mock_callable(sample_module, "test_function").for_call(
            testslide.matchers.RegexMatches("foo"),
            testslide.matchers.RegexMatches("bar"),
        ).to_return_value(["mocked_response"])
        with self.assertRaises(testslide.mock_callable.UnexpectedCallArguments):
            sample_module.test_function("meh", "moh")
        sample_module.test_function("foo", "bar")
