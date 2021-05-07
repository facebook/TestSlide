# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.
import re
from typing import Any as AnyType
from typing import Callable, Dict, List, NoReturn, Optional, TypeVar, Union


class AlreadyChainedException(Exception):
    pass


class _AlreadyChainedMatcher:
    """
    Disallow further chaining of equality of objects.
    """

    def __and__(self, other: object) -> NoReturn:
        raise AlreadyChainedException("Cannot chain more than two matchers")

    def __xor__(self, other: object) -> NoReturn:
        raise AlreadyChainedException("Cannot chain more than two matchers")

    def __invert__(self) -> NoReturn:
        raise AlreadyChainedException("Cannot chain more than two matchers")

    def __or__(self, other: object) -> NoReturn:
        raise AlreadyChainedException("Cannot chain more than two matchers")


class Matcher:
    """
    Allows composition of equality of objects by using bitwise operations.
    """

    def __and__(self, other: "Matcher") -> "_AndMatcher":
        return _AndMatcher(self, other)

    def __xor__(self, other: "Matcher") -> "_XorMatcher":
        return _XorMatcher(self, other)

    def __invert__(self) -> "_InvMatcher":
        return _InvMatcher(self)

    def __or__(self, other: "Matcher") -> "_OrMatcher":
        return _OrMatcher(self, other)


class _AndMatcher(_AlreadyChainedMatcher):
    """
    Equality is true if both "a" and "b" are true.
    """

    def __init__(self, a: Matcher, b: Matcher) -> None:
        self.a = a
        self.b = b

    def __eq__(self, other: AnyType) -> bool:
        return self.a == other and self.b == other

    def __repr__(self) -> str:
        return f"{self.a} & {self.b}"


class _XorMatcher(_AlreadyChainedMatcher):
    def __init__(self, a: Matcher, b: Matcher) -> None:
        self.a = a
        self.b = b

    def __eq__(self, other: AnyType) -> bool:
        return (self.a == other or self.b != other) and (
            self.a != other or self.b == other
        )

    def __repr__(self) -> str:
        return f"{self.a} ^ {self.b}"


class _InvMatcher(_AlreadyChainedMatcher):
    def __init__(self, matcher: Matcher) -> None:
        self.matcher = matcher

    def __eq__(self, other: AnyType) -> bool:
        return not (self.matcher == other)

    def __repr__(self) -> str:
        return f"! {self.matcher}"


class _OrMatcher(_AlreadyChainedMatcher):
    def __init__(self, a: Matcher, b: Matcher) -> None:
        self.a = a
        self.b = b

    def __eq__(self, other: AnyType) -> bool:
        return self.a == other or self.b == other

    def __repr__(self) -> str:
        return f"{self.a} | {self.b}"


class _RichComparison(Matcher):
    def __init__(
        self,
        klass: type,
        lt: Optional[AnyType] = None,
        le: Optional[AnyType] = None,
        eq: Optional[AnyType] = None,
        ne: Optional[AnyType] = None,
        ge: Optional[AnyType] = None,
        gt: Optional[AnyType] = None,
    ) -> None:
        self.klass = klass
        self.lt = lt
        self.le = le
        self.eq = eq
        self.ne = ne
        self.ge = ge
        self.gt = gt

    def __eq__(self, other: AnyType) -> bool:
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

    def __repr__(self) -> str:
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


class _FloatComparison(_RichComparison):
    """
    Compares true if other number passes all rich comparison cases given.
    """

    def __init__(
        self,
        lt: Optional[Union[float, int]] = None,
        le: Optional[Union[float, int]] = None,
        eq: Optional[Union[float, int]] = None,
        ne: Optional[Union[float, int]] = None,
        ge: Optional[Union[float, int]] = None,
        gt: Optional[Union[float, int]] = None,
    ) -> None:
        super().__init__(float, lt=lt, le=le, eq=eq, ne=ne, ge=ge, gt=gt)


class _IntComparison(_RichComparison):
    """
    Compares true if other number passes all rich comparison cases given.
    """

    def __init__(
        self,
        lt: Optional[Union[float, int]] = None,
        le: Optional[Union[float, int]] = None,
        eq: Optional[Union[float, int]] = None,
        ne: Optional[Union[float, int]] = None,
        ge: Optional[Union[float, int]] = None,
        gt: Optional[Union[float, int]] = None,
    ) -> None:
        super().__init__(int, lt=lt, le=le, eq=eq, ne=ne, ge=ge, gt=gt)


# Ints
class AnyInt(_IntComparison):
    def __init__(self) -> None:
        super().__init__()


class NotThisInt(_IntComparison):
    def __init__(self, ne: int) -> None:
        if not isinstance(ne, int):
            raise ValueError(
                f"NotThisInt(...) expects an 'int' as argument while '{type(ne).__name__}' was provided"
            )
        super().__init__(ne=ne)


class IntBetween(_IntComparison):
    def __init__(self, lower: int, upper: int) -> None:
        if not isinstance(lower, (int, float)) or not isinstance(upper, (int, float)):
            raise ValueError(
                f"IntBetween(...) expects two numerical values as arguments while '{type(lower).__name__}' and '{type(upper).__name__}' were provided"
            )
        super().__init__(ge=lower, le=upper)


class IntGreaterThan(_IntComparison):
    def __init__(self, gt: int) -> None:
        if not isinstance(gt, (int, float)):
            raise ValueError(
                f"IntGreaterThan(...) expects a numerical value as argument while '{type(gt).__name__}' was provided"
            )
        super().__init__(gt=gt)


class IntGreaterOrEquals(_IntComparison):
    def __init__(self, ge: int) -> None:
        if not isinstance(ge, (int, float)):
            raise ValueError(
                f"IntGreaterOrEquals(...) expects a numerical value as argument while '{type(ge).__name__}' was provided"
            )
        super().__init__(ge=ge)


class IntLessThan(_IntComparison):
    def __init__(self, lt: int) -> None:
        if not isinstance(lt, (int, float)):
            raise ValueError(
                f"IntLessThan(...) expects a numerical value as argument while '{type(lt).__name__}' was provided"
            )
        super().__init__(lt=lt)


class IntLessOrEquals(_IntComparison):
    def __init__(self, le: int) -> None:
        if not isinstance(le, (int, float)):
            raise ValueError(
                f"IntLessOrEquals(...) expects a numerical value as argument while '{type(le).__name__}' was provided"
            )
        super().__init__(le=le)


# floats
class AnyFloat(_FloatComparison):
    def __init__(self) -> None:
        super().__init__()


class NotThisFloat(_FloatComparison):
    def __init__(self, ne: float) -> None:
        if not isinstance(ne, float):
            raise ValueError(
                f"NotThisFloat(...) expects a 'float' as argument while '{type(ne).__name__}' was provided"
            )
        super().__init__(ne=ne)


class FloatBetween(_FloatComparison):
    def __init__(self, lower: float, upper: float) -> None:
        if not isinstance(lower, (int, float)) or not isinstance(upper, (int, float)):
            raise ValueError(
                f"FloatBetween(...) expects numerical values as arguments while '{type(lower).__name__}' and '{type(upper).__name__}' were provided"
            )
        super().__init__(ge=lower, le=upper)


class FloatGreaterThan(_FloatComparison):
    def __init__(self, gt: float) -> None:
        if not isinstance(gt, (int, float)):
            raise ValueError(
                f"FloatGreaterThan(...) expects a numerical value as argument while '{type(gt).__name__}' was provided"
            )
        super().__init__(gt=gt)


class FloatGreaterOrEquals(_FloatComparison):
    def __init__(self, ge: float) -> None:
        if not isinstance(ge, (int, float)):
            raise ValueError(
                f"FloatGreaterOrEquals(...) expects a numerical value as argument while '{type(ge).__name__}' was provided"
            )
        super().__init__(ge=ge)


class FloatLessThan(_FloatComparison):
    def __init__(self, lt: float) -> None:
        if not isinstance(lt, (int, float)):
            raise ValueError(
                f"FloatLessThan(...) expects a numerical value as argument while '{type(lt).__name__}' was provided"
            )
        super().__init__(lt=lt)


class FloatLessOrEquals(_FloatComparison):
    def __init__(self, le: float) -> None:
        if not isinstance(le, (int, float)):
            raise ValueError(
                f"FloatLessOrEquals(...) expects a numerical value as argument while '{type(le).__name__}' was provided"
            )
        super().__init__(le=le)


# strings


class AnyStr(_RichComparison):
    def __init__(self) -> None:
        super().__init__(klass=str)


class RegexMatches(Matcher):
    """
    Compares true if other matches given regex.
    """

    def __init__(self, pattern: str, flags: int = 0) -> None:
        self.pattern = pattern
        self.flags = flags
        self.prog = re.compile(pattern, flags)

    def __eq__(self, other: AnyType) -> bool:
        if not isinstance(other, str):
            return False
        return bool(self.prog.match(other))

    def __repr__(self) -> str:
        return "<RegexMatches 0x{:02X} pattern={}{}>".format(
            id(self),
            repr(self.pattern),
            f" flags={self.flags}" if self.flags != 0 else "",
        )


class StrContaining(Matcher):
    def __init__(self, needle: str) -> None:
        if not isinstance(needle, str):
            raise ValueError(
                f"StrContaining(...) expects a 'str' as argument while '{type(needle).__name__}' was provided"
            )
        self.needle = needle

    def __eq__(self, other: AnyType) -> bool:
        return isinstance(other, str) and self.needle in other


class StrStartingWith(Matcher):
    def __init__(self, needle: str) -> None:
        if not isinstance(needle, str):
            raise ValueError(
                f"StrStartingWith(...) expects a 'str' as argument while '{type(needle).__name__}' was provided"
            )
        self.needle = needle

    def __eq__(self, other: AnyType) -> bool:
        return isinstance(other, str) and other.startswith(self.needle)


class StrEndingWith(Matcher):
    def __init__(self, needle: str) -> None:
        if not isinstance(needle, str):
            raise ValueError(
                f"StrEndingWith(...) expects a 'str' as argument while '{type(needle).__name__}' was provided"
            )
        self.needle = needle

    def __eq__(self, other: AnyType) -> bool:  # type: ignore
        return isinstance(other, str) and other.endswith(self.needle)


# lists
class AnyList(_RichComparison):
    def __init__(self) -> None:
        super().__init__(klass=List)


class ListContaining(_RichComparison):
    def __init__(self, needle: AnyType) -> None:
        self.needle = needle
        super().__init__(klass=List)

    def __eq__(self, other: List[AnyType]) -> bool:  # type: ignore
        return super().__eq__(other) and self.needle in other

    def __repr__(self) -> str:
        return "<{} 0x{:02X}{}>".format(
            type(self).__name__,
            id(self),
            f" needle={self.needle}" if self.needle is not None else "",
        )


class ListContainingAll(_RichComparison):
    def __init__(self, subset: List[AnyType]) -> None:
        if not isinstance(subset, list):
            raise ValueError(
                f"ListContainingAll(...) expects a 'list' as argument while '{type(subset).__name__}' was provided"
            )
        self.subset = subset
        super().__init__(klass=List)

    def __eq__(self, other: List[AnyType]) -> bool:  # type: ignore
        return super().__eq__(other) and all(x in other for x in self.subset)

    def __repr__(self) -> str:
        return "<{} 0x{:02X}{}>".format(
            type(self).__name__,
            id(self),
            f" subset={self.subset}" if self.subset is not None else "",
        )


class NotEmptyList(AnyList):
    def __eq__(self, other: List[AnyType]) -> bool:  # type: ignore
        return super().__eq__(other) and bool(other)


class EmptyList(AnyList):
    def __eq__(self, other: List[AnyType]):  # type: ignore
        return super().__eq__(other) and not bool(other)


# dicts
class AnyDict(_RichComparison):
    def __init__(self) -> None:
        super().__init__(klass=Dict)


class NotEmptyDict(AnyDict):
    def __eq__(self, other: Optional[Dict[AnyType, AnyType]]) -> bool:  # type: ignore
        return super().__eq__(other) and bool(other)


class EmptyDict(AnyDict):
    def __eq__(self, other: Optional[Dict[AnyType, AnyType]]) -> bool:  # type: ignore
        return super().__eq__(other) and not bool(other)


class DictContainingKeys(_RichComparison):
    def __init__(self, expected_keys: List[AnyType]) -> None:
        if not isinstance(expected_keys, list):
            raise ValueError(
                f"DictContainingKeys(...) expects a 'list' as argument while '{type(expected_keys).__name__}' was provided"
            )
        self.expected_keys = expected_keys
        super().__init__(klass=Dict)

    def __eq__(self, other: Dict[AnyType, AnyType]) -> bool:  # type: ignore
        try:
            return super().__eq__(other) and all(
                attr in other for attr in self.expected_keys
            )
        except KeyError:
            return False


class DictSupersetOf(_RichComparison):
    def __init__(self, subset: Dict[AnyType, AnyType]) -> None:
        if not isinstance(subset, dict):
            raise ValueError(
                f"DictSupersetOf(...) expects a 'dict' as argument while '{type(subset).__name__}' was provided"
            )
        self.subset = subset
        super().__init__(klass=Dict)

    def __eq__(self, other: Dict[AnyType, AnyType]) -> bool:  # type: ignore
        try:
            return super().__eq__(other) and all(
                other[attr] == self.subset[attr] for attr in self.subset.keys()
            )
        except KeyError:
            return False


# generic


class Any(Matcher):
    def __eq__(self, other: AnyType) -> bool:  # type: ignore
        return True


class AnyTruthy(Matcher):
    def __eq__(self, other: AnyType) -> bool:  # type: ignore
        return bool(other)


class AnyFalsey(Matcher):
    def __eq__(self, other: AnyType) -> bool:  # type: ignore
        return not bool(other)


class AnyInstanceOf(_RichComparison):
    def __init__(self, klass: type) -> None:
        if not isinstance(klass, type):
            raise ValueError(
                "AnyInstanceOf(...) expects a type while a '{}' ('{}') was provided".format(
                    type(klass).__name__, klass
                )
            )
        super().__init__(klass=klass)


T = TypeVar("T")


class AnyWithCall(Matcher):
    def __init__(self, call: Callable[[T], bool]) -> None:
        self.call = call

    def __eq__(self, other: T) -> bool:
        return self.call(other)
