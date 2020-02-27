#!/usr/bin/env python3
# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.
import re
from typing import List, Dict

class AlreadyChainedException(Exception):
    pass


class _AlreadyChainedMatcher:
    """
    Disallow further chaining of equality of objects.

    """

    def __and__(self, other):
        raise AlreadyChainedException("Cannot chain more than two matchers")

    def __xor__(self, other):
        raise AlreadyChainedException("Cannot chain more than two matchers")

    def __inv__(self):
        raise AlreadyChainedException("Cannot chain more than two matchers")

    def __or__(self, other):
        raise AlreadyChainedException("Cannot chain more than two matchers")


class _Matcher:
    """
    Allows composition of equality of objects by using bitwise operations.
    """

    def __and__(self, other):
        return _AndMatcher(self, other)

    def __xor__(self, other):
        return _XorMatcher(self, other)

    def __inv__(self):
        return _InvMatcher(self)

    def __or__(self, other):
        return _OrMatcher(self, other)


class _AndMatcher(_AlreadyChainedMatcher):
    """
    Equality is true if both "a" and "b" are true.
    """

    def __init__(self, a, b):
        self.a = a
        self.b = b

    def __eq__(self, other):
        return self.a == other and self.b == other

    def __repr__(self):
        return f"{self.a} & {self.b}"


class _XorMatcher(_AlreadyChainedMatcher):
    def __init__(self, a, b):
        self.a = a
        self.b = b

    def __eq__(self, other):
        return (self.a == other or self.b != other) and (
            self.a != other or self.b == other
        )

    def __repr__(self):
        return f"{self.a} ^ {self.b}"


class _InvMatcher(_AlreadyChainedMatcher):
    def __init__(self, matcher):
        self.matcher = matcher

    def __eq__(self, other):
        return not (self.matcher == other)

    def __repr__(self):
        return f"! {self.matcher}"


class _OrMatcher(_AlreadyChainedMatcher):
    def __init__(self, a, b):
        self.a = a
        self.b = b

    def __eq__(self, other):
        return self.a == other or self.b == other

    def __repr__(self):
        return f"{self.a} | {self.b}"


class RegexMatches(_Matcher):
    """
    Compares true if other mathes given regex.
    """

    def __init__(self, pattern, flags=0):
        self.pattern = pattern
        self.flags = flags
        self.prog = re.compile(pattern, flags)

    def __eq__(self, other):
        if not isinstance(other, str):
            return False
        return bool(self.prog.match(other))

    def __repr__(self):
        return "<RegexMatches 0x{:02X} pattern={}{}>".format(
            id(self),
            repr(self.pattern),
            f" flags={self.flags}" if self.flags != 0 else "",
        )


class _RichComparison(_Matcher):
    def __init__(self, klass, lt=None, le=None, eq=None, ne=None, ge=None, gt=None):
        self.klass = klass
        self.lt = lt
        self.le = le
        self.eq = eq
        self.ne = ne
        self.ge = ge
        self.gt = gt

    def __eq__(self, other):
        if not isinstance(other, self.klass):
            return False
        if self.lt is not None and not (other < self.lt):
            return False
        if self.le is not None and not (other <= self.le):
            return False
        if self.eq is not None and not (other == self.eq):
            return False
        if self.ne is not None and not (other != self.ne):
            return False
        if self.ge is not None and not (other >= self.ge):
            return False
        if self.gt is not None and not (other > self.gt):
            return False
        return True

    def __repr__(self):
        return "<{} 0x{:02X}{}{}{}{}{}{}>".format(
            type(self).__name__,
            id(self),
            f" lt={self.lt}" if self.lt is not None else "",
            f" le={self.le}" if self.le is not None else "",
            f" eq={self.eq}" if self.eq is not None else "",
            f" ne={self.ne}" if self.ne is not None else "",
            f" ge={self.ge}" if self.ge is not None else "",
            f" gt={self.gt}" if self.gt is not None else "",
        )


class float_comparison(_RichComparison):
    """
    Compares true if other number passes all rich comparison cases given.
    """

    def __init__(self, lt=None, le=None, eq=None, ne=None, ge=None, gt=None):
        super().__init__(float, lt=lt, le=le, eq=eq, ne=ne, ge=ge, gt=gt)


class int_comparison(_RichComparison):
    """
    Compares true if other number passes all rich comparison cases given.
    """

    def __init__(self, lt=None, le=None, eq=None, ne=None, ge=None, gt=None):
        super().__init__(int, lt=lt, le=le, eq=eq, ne=ne, ge=ge, gt=gt)

AnyInt = int_comparison

class ThisInt(int_comparison):
    def __init__(self, eq):
        super().__init__(eq=eq)


class NotThisInt(int_comparison):
    def __init__(self, ne: int):
        super().__init__(ne=ne)


class IntBetween(int_comparison):
    def __init__(self, lower: int, upper: int):
        super().__init__(ge=lower, le=upper)


class IntGreater(int_comparison):
    def __init__(self, gt: int):
        super().__init__(gt=gt)


class IntGreaterOrEquals(int_comparison):
    def __init__(self, ge: int):
        super().__init__(ge=ge)


class IntLess(int_comparison):
    def __init__(self, lt):
        super().__init__(lt=lt)

class IntLessOrEquals(int_comparison):
    def __init__(self, le):
        super().__init__(le=le)

AnyFloat = float_comparison

class ThisFloat(float_comparison):
    def __init__(self, eq):
        super().__init__(eq=eq)


class NotThisFloat(float_comparison):
    def __init__(self, ne: float):
        super().__init__(ne=ne)


class FloatBetween(float_comparison):
    def __init__(self, lower: float, upper: float):
        super().__init__(ge=lower, le=upper)


class FloatGreater(float_comparison):
    def __init__(self, gt: float):
        super().__init__(gt=gt)


class FloatGreaterOrEquals(float_comparison):
    def __init__(self, ge: float):
        super().__init__(ge=ge)


class FloatLess(float_comparison):
    def __init__(self, lt):
        super().__init__(lt=lt)


class FloatLessOrEquals(float_comparison):
    def __init__(self, le):
        super().__init__(le=le)


class NotEmpty(_Matcher):
    def __eq__(self, other):
        return bool(other)


class Empty(_Matcher):
    def __eq__(self, other):
        return not bool(other)


class Something(_Matcher):
    def __eq__(self, other):
        return other is not None


class Nothing(_Matcher):
    def __eq__(self, other):
        return other is None

class AnyString(_RichComparison):
    def __init__(self):
        super().__init__(klass=str)

class ListContaining(_RichComparison):
    def __init__(self, subset:List):
        self.subset = subset
        super().__init__(klass=List)

    def __eq__(self, other):
        return super().__eq__(other) and all(x in other for x in self.subset)

    def __repr__(self):
        return "<{} 0x{:02X}{}>".format(
            type(self).__name__,
            id(self),
            f" subset={self.subset}" if self.subset is not None else "",
        )


class DictContaining(_RichComparison):
    def __init__(self, subset:Dict):
        self.subset = subset
        super().__init__(klass=Dict)

    def __eq__(self, other):
        try:
            return super().__eq__(other) and all(
                other[attr] == self.subset[attr] for attr in self.subset.keys()
            )
        except KeyError:
            return False


class A(_RichComparison):
    def __init__(self, klass):
        super().__init__(klass=klass)
