# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import asyncio
import functools
import inspect
from inspect import Traceback
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Tuple,
    Type,
    Union,
)
from unittest.mock import Mock

import testslide
from testslide.lib import _validate_return_type, _wrap_signature_and_type_validation
from testslide.strict_mock import StrictMock

from .lib import CoroutineValueError, _bail_if_private, _is_a_builtin
from .patch import _is_instance_method, _patch

if TYPE_CHECKING:
    from testslide.matchers import RegexMatches  # noqa: F401
    from testslide.mock_constructor import _MockConstructorDSL  # noqa: F401


def mock_callable(
    target: Any,
    method: str,
    allow_private: bool = False,
    # type_validation accepted values:
    #  * None:  type validation will be enabled except if target is a StrictMock
    #           with disabled type validation
    #  * True:  type validation will be enabled (regardless of target type)
    #  * False:  type validation will be disabled
    type_validation: Optional[bool] = None,
) -> "_MockCallableDSL":
    caller_frame = inspect.currentframe().f_back  # type: ignore
    # loading the context ends up reading files from disk and that might block
    # the event loop, so we don't do it.
    caller_frame_info = inspect.getframeinfo(caller_frame, context=0)  # type: ignore
    return _MockCallableDSL(
        target,
        method,
        caller_frame_info,
        allow_private=allow_private,
        type_validation=type_validation,
    )


def mock_async_callable(
    target: Union[type, str],
    method: str,
    callable_returns_coroutine: bool = False,
    allow_private: bool = False,
    type_validation: bool = True,
) -> "_MockAsyncCallableDSL":
    caller_frame = inspect.currentframe().f_back  # type: ignore
    # loading the context ends up reading files from disk and that might block
    # the event loop, so we don't do it.
    caller_frame_info = inspect.getframeinfo(caller_frame, context=0)  # type: ignore
    return _MockAsyncCallableDSL(
        target,
        method,
        caller_frame_info,
        callable_returns_coroutine,
        allow_private,
        type_validation,
    )


_unpatchers: List[Callable] = []  # noqa T484


def _default_register_assertion(assertion: Callable) -> None:
    """
    This method must be redefined by the test framework using mock_callable().
    It will be called when a new assertion is defined, passing a callable as an
    argument that evaluates that assertion. Every defined assertion during a test
    must be called after the test code ends, and before the test finishes.
    """
    raise NotImplementedError("This method must be redefined by the test framework")


register_assertion = _default_register_assertion
_call_order_assertion_registered: bool = False
_received_ordered_calls: List[Tuple[Any, str, "_BaseRunner"]] = []
_expected_ordered_calls: List[Tuple[Any, str, "_BaseRunner"]] = []


def unpatch_all_callable_mocks() -> None:
    """
    This method must be called after every test unconditionally to remove all
    active mock_callable() patches.
    """
    global register_assertion, _default_register_assertion, _call_order_assertion_registered, _received_ordered_calls, _expected_ordered_calls

    register_assertion = _default_register_assertion
    _call_order_assertion_registered = False
    del _received_ordered_calls[:]
    del _expected_ordered_calls[:]

    unpatch_exceptions = []
    for unpatcher in _unpatchers:
        try:
            unpatcher()
        except Exception as e:
            unpatch_exceptions.append(e)
    del _unpatchers[:]
    if unpatch_exceptions:
        raise RuntimeError(
            "Exceptions raised when unpatching: {}".format(unpatch_exceptions)
        )


def _is_setup() -> bool:
    global register_assertion, _default_register_assertion
    return register_assertion is not _default_register_assertion


def _format_target(target: Union[str, type]) -> str:
    if hasattr(target, "__repr__"):
        return repr(target)
    else:
        return "{}.{} instance with id {}".format(
            target.__module__, type(target).__name__, id(target)
        )


def _format_args(indent: int, *args: Any, **kwargs: Any) -> str:
    indentation = "  " * indent
    s = ""
    if args:
        s += ("{}{}\n").format(indentation, args)
    if kwargs:
        s += indentation + "{"
        if kwargs:
            s += "\n"
            for k in sorted(kwargs.keys()):
                s += "{}  {}={},\n".format(indentation, k, kwargs[k])
            s += "{}".format(indentation)
        s += "}\n"
    return s


def _is_coroutine(obj: Any) -> bool:

    return inspect.iscoroutine(obj) or isinstance(obj, asyncio.coroutines.CoroWrapper)  # type: ignore


def _is_coroutinefunction(func: Any) -> bool:
    # We use asyncio.iscoroutinefunction over inspect because the next Cython version
    # will return True from the asyncio variant over inspect which will return False
    # FIXME We can not reliably introspect coroutine functions
    # for builtins: https://bugs.python.org/issue38225
    return asyncio.iscoroutinefunction(func) or _is_a_builtin(func)


##
## Exceptions
##


class UndefinedBehaviorForCall(BaseException):
    """
    Raised when a mock receives a call for which no behavior was defined.

    Inherits from BaseException to avoid being caught by tested code.
    """


class UnexpectedCallReceived(BaseException):
    """
    Raised when a mock receives a call that it is configured not to accept.

    Inherits from BaseException to avoid being caught by tested code.
    """


class UnexpectedCallArguments(BaseException):
    """
    Raised when a mock receives a call with unexpected arguments.

    Inherits from BaseException to avoid being caught by tested code.
    """


class NotACoroutine(BaseException):
    """
    Raised when a mock that requires a coroutine is not mocked with one.

    Inherits from BaseException to avoid being caught by tested code.
    """


##
## Runners
##


class _BaseRunner:
    TYPE_VALIDATION = True

    def __init__(
        self, target: Any, method: str, original_callable: Union[Callable, Mock]
    ) -> None:
        self.target = target
        self.method = method
        self.original_callable = original_callable
        self.accepted_args: Optional[Tuple[Any, Any]] = None

        self._call_count: int = 0
        self._max_calls: Optional[int] = None
        self._has_order_assertion = False

    def register_call(self, *args: Any, **kwargs: Any) -> None:
        global _received_ordered_calls

        if self._has_order_assertion:
            _received_ordered_calls.append((self.target, self.method, self))

        self.inc_call_count()

    @property
    def call_count(self) -> int:
        return self._call_count

    @property
    def max_calls(self) -> Optional[int]:
        return self._max_calls

    def _set_max_calls(self, times: int) -> None:
        if not self._max_calls or times < self._max_calls:
            self._max_calls = times

    def inc_call_count(self) -> None:
        self._call_count += 1
        if self.max_calls and self._call_count > self.max_calls:
            raise UnexpectedCallReceived(
                (
                    "Unexpected call received.\n"
                    "{}, {}:\n"
                    "  expected to receive at most {} calls with {}"
                    "  but received an extra call."
                ).format(
                    _format_target(self.target),
                    repr(self.method),
                    self.max_calls,
                    self._args_message(),
                )
            )

    def add_accepted_args(self, *args: Any, **kwargs: Any) -> None:
        # TODO validate if args match callable signature
        self.accepted_args = (args, kwargs)

    def can_accept_args(self, *args: Any, **kwargs: Any) -> bool:
        if self.accepted_args:
            if self.accepted_args == (args, kwargs):
                return True
            return False
        else:
            return True

    def _args_message(self) -> str:
        if self.accepted_args:
            return "arguments:\n{}".format(
                _format_args(2, *self.accepted_args[0], **self.accepted_args[1])
            )
        else:
            return "any arguments "

    def add_exact_calls_assertion(self, times: int) -> None:
        self._set_max_calls(times)

        def assertion() -> None:
            if times != self.call_count:
                raise AssertionError(
                    (
                        "calls did not match assertion.\n"
                        "{}, {}:\n"
                        "  expected: called exactly {} time(s) with {}"
                        "  received: {} call(s)"
                    ).format(
                        _format_target(self.target),
                        repr(self.method),
                        times,
                        self._args_message(),
                        self.call_count,
                    )
                )

        register_assertion(assertion)

    def add_at_least_calls_assertion(self, times: int) -> None:
        def assertion() -> None:
            if self.call_count < times:
                raise AssertionError(
                    (
                        "calls did not match assertion.\n"
                        "{}, {}:\n"
                        "  expected: called at least {} time(s) with {}"
                        "  received: {} call(s)"
                    ).format(
                        _format_target(self.target),
                        repr(self.method),
                        times,
                        self._args_message(),
                        self.call_count,
                    )
                )

        register_assertion(assertion)

    def add_at_most_calls_assertion(self, times: int) -> None:
        self._set_max_calls(times)

        def assertion() -> None:
            if not self.call_count or self.call_count > times:
                raise AssertionError(
                    (
                        "calls did not match assertion.\n"
                        "{}, {}:\n"
                        "  expected: called at most {} time(s) with {}"
                        "  received: {} call(s)"
                    ).format(
                        _format_target(self.target),
                        repr(self.method),
                        times,
                        self._args_message(),
                        self.call_count,
                    )
                )

        register_assertion(assertion)

    def add_call_order_assertion(self) -> None:
        global _call_order_assertion_registered, _received_ordered_calls, _expected_ordered_calls

        if not _call_order_assertion_registered:

            def assertion() -> None:
                if _received_ordered_calls != _expected_ordered_calls:
                    raise AssertionError(
                        (
                            "calls did not match assertion.\n"
                            "\n"
                            "These calls were expected to have happened in order:\n"
                            "\n"
                            "{}\n"
                            "\n"
                            "but these calls were made:\n"
                            "\n"
                            "{}"
                        ).format(
                            "\n".join(
                                (
                                    "  {}, {} with {}".format(
                                        _format_target(target),
                                        repr(method),
                                        runner._args_message().rstrip(),
                                    )
                                    for target, method, runner in _expected_ordered_calls
                                )
                            ),
                            "\n".join(
                                (
                                    "  {}, {} with {}".format(
                                        _format_target(target),
                                        repr(method),
                                        runner._args_message().rstrip(),
                                    )
                                    for target, method, runner in _received_ordered_calls
                                )
                            ),
                        )
                    )

            register_assertion(assertion)
            _call_order_assertion_registered = True

        _expected_ordered_calls.append((self.target, self.method, self))
        self._has_order_assertion = True


class _Runner(_BaseRunner):
    def run(self, *args: Any, **kwargs: Any) -> None:
        super().register_call(*args, **kwargs)


class _AsyncRunner(_BaseRunner):
    async def run(self, *args: Any, **kwargs: Any) -> None:
        super().register_call(*args, **kwargs)


class _ReturnValueRunner(_Runner):
    def __init__(
        self,
        target: Any,
        method: str,
        original_callable: Union[Callable, Mock],
        value: Optional[Any],
        allow_coro: bool = False,
    ) -> None:
        super().__init__(target, method, original_callable)
        if not allow_coro and _is_coroutine(value):
            raise CoroutineValueError()
        self.return_value = value

    def run(self, *args: Any, **kwargs: Any) -> Optional[Any]:
        super().run(*args, **kwargs)
        return self.return_value


class _ReturnValuesRunner(_Runner):
    def __init__(
        self,
        target: Union[type, str],
        method: str,
        original_callable: Union[Callable[..., Any], Mock],
        values_list: List[Any],
        allow_coro: bool = False,
    ) -> None:
        super(_ReturnValuesRunner, self).__init__(target, method, original_callable)
        # Reverse original list for popping efficiency
        if not allow_coro and any(_is_coroutine(rv) for rv in values_list):
            raise CoroutineValueError()
        self.values_list = list(reversed(values_list))

    def run(self, *args: Any, **kwargs: Any) -> Any:
        super(_ReturnValuesRunner, self).run(*args, **kwargs)
        if self.values_list:
            return self.values_list.pop()
        else:
            raise UndefinedBehaviorForCall("No more values to return!")


class _YieldValuesRunner(_Runner):
    TYPE_VALIDATION = False

    def __init__(
        self,
        target: Union[type, str],
        method: str,
        original_callable: Union[Callable[..., Any], Mock],
        values_list: List[Any],
        allow_coro: bool = False,
    ) -> None:
        super(_YieldValuesRunner, self).__init__(target, method, original_callable)
        self.values_list = values_list
        self.index = 0
        if not allow_coro and any(_is_coroutine(rv) for rv in values_list):
            raise CoroutineValueError()

    def __iter__(self) -> "_YieldValuesRunner":
        return self

    def __next__(self) -> Any:
        try:
            item = self.values_list[self.index]
        except IndexError:
            raise StopIteration()
        self.index += 1
        return item

    def run(self, *args: Any, **kwargs: Any) -> "_YieldValuesRunner":  # type: ignore
        super(_YieldValuesRunner, self).run(*args, **kwargs)
        return self


class _RaiseRunner(_Runner):
    def __init__(
        self,
        target: Union[type, str],
        method: str,
        original_callable: Union[Callable[..., Any], Mock],
        exception: BaseException,
    ) -> None:
        super(_RaiseRunner, self).__init__(target, method, original_callable)
        self.exception = exception

    def run(self, *args: Any, **kwargs: Any) -> None:
        super(_RaiseRunner, self).run(*args, **kwargs)
        raise self.exception


class _ImplementationRunner(_Runner):
    def __init__(
        self,
        target: Union[type, str],
        method: str,
        original_callable: Union[Callable[..., Any], Mock],
        new_implementation: Callable,
        allow_coro: bool = False,
    ) -> None:
        super(_ImplementationRunner, self).__init__(target, method, original_callable)
        self.new_implementation = new_implementation
        self._allow_coro = allow_coro

    def run(self, *args: Any, **kwargs: Any) -> Optional[Any]:
        super(_ImplementationRunner, self).run(*args, **kwargs)
        new_impl = self.new_implementation(*args, **kwargs)
        if not self._allow_coro and _is_coroutine(new_impl):
            raise CoroutineValueError()
        return new_impl


class _AsyncImplementationRunner(_AsyncRunner):
    def __init__(
        self,
        target: Union[type, str],
        method: str,
        original_callable: Union[Callable[..., Any], Mock],
        new_implementation: Callable,
    ) -> None:
        super().__init__(target, method, original_callable)
        self.new_implementation = new_implementation

    async def run(self, *args: Any, **kwargs: Any) -> Optional[Any]:
        await super().run(*args, **kwargs)
        coro = self.new_implementation(*args, **kwargs)
        if not _is_coroutine(coro):
            raise NotACoroutine(
                f"Function did not return a coroutine.\n"
                f"{self.new_implementation} must return a coroutine."
            )
        return await coro


class _CallOriginalRunner(_Runner):
    def run(self, *args: Any, **kwargs: Any) -> Optional[Any]:
        super(_CallOriginalRunner, self).run(*args, **kwargs)
        return self.original_callable(*args, **kwargs)


class _AsyncCallOriginalRunner(_AsyncRunner):
    async def run(self, *args: Any, **kwargs: Any) -> Optional[Any]:
        await super().run(*args, **kwargs)
        return await self.original_callable(*args, **kwargs)


##
## Callable Mocks
##


class _CallableMock:
    def __init__(
        self,
        target: Any,
        method: str,
        caller_frame_info: Traceback,
        is_async: bool = False,
        # type_validation accepted values:
        #  * None:  type validation will be enabled except if target is a StrictMock
        #           with disabled type validation
        #  * True:  type validation will be enabled (regardless of target type)
        #  * False:  type validation will be disabled
        type_validation: Optional[bool] = None,
    ) -> None:
        self.target = target
        self.method = method
        self.runners: List[_BaseRunner] = []
        self.is_async = is_async
        self.type_validation = type_validation or type_validation is None
        self.caller_frame_info = caller_frame_info

        if type_validation is None and isinstance(target, StrictMock):
            # If type validation is enabled on the specific call
            # but the StrictMock has type validation disabled then
            # type validation should be disabled
            self.type_validation = target._type_validation

    def _get_runner(self, *args: Any, **kwargs: Any) -> Any:
        for runner in self.runners:
            if runner.can_accept_args(*args, **kwargs):
                return runner
        return None

    def _validate_return_type(self, runner: _BaseRunner, value: Any) -> None:
        if self.type_validation and runner.TYPE_VALIDATION:
            if runner.original_callable is not None:
                _validate_return_type(
                    runner.original_callable, value, self.caller_frame_info
                )
            elif isinstance(runner.target, StrictMock):
                _validate_return_type(
                    getattr(runner.target, runner.method), value, self.caller_frame_info
                )

    def __call__(self, *args: Any, **kwargs: Any) -> Optional[Any]:
        runner = self._get_runner(*args, **kwargs)
        if runner:
            if self.is_async:
                if isinstance(runner, _AsyncRunner):

                    async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                        value = await runner.run(*args, **kwargs)
                        self._validate_return_type(runner, value)
                        return value

                    value = async_wrapper(*args, **kwargs)
                else:

                    async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                        value = runner.run(*args, **kwargs)
                        self._validate_return_type(runner, value)
                        return value

                    value = async_wrapper(*args, **kwargs)
            else:
                value = runner.run(*args, **kwargs)
                self._validate_return_type(runner, value)
            return value
        else:
            ex_msg = (
                "{}, {}:\n"
                "  Received call:\n"
                "{}"
                "  But no behavior was defined for it."
            ).format(
                _format_target(self.target),
                repr(self.method),
                _format_args(2, *args, **kwargs),
            )
            if self._registered_calls:
                ex_msg += "\n  These are the registered calls:\n" "{}".format(
                    "".join(
                        _format_args(2, *reg_args, **reg_kwargs)
                        for reg_args, reg_kwargs in self._registered_calls
                    )
                )
                raise UnexpectedCallArguments(ex_msg)
            raise UndefinedBehaviorForCall(ex_msg)

    @property
    def _registered_calls(self) -> Any:
        return [runner.accepted_args for runner in self.runners if runner.accepted_args]


##
## Support
##


class _MockCallableDSL:

    CALLABLE_MOCKS: Dict[
        Union[int, Tuple[int, str]], Union[Callable[[Type[object]], Any]]
    ] = {}
    _NAME: str = "mock_callable"

    def _validate_patch(
        self,
        name: str = "mock_callable",
        other_name: str = "mock_async_callable",
        coroutine_function: bool = False,
        callable_returns_coroutine: bool = False,
    ) -> None:
        if self._method == "__new__":
            raise ValueError(
                f"Mocking __new__ is not allowed with {name}(), please use "
                "mock_constructor()."
            )
        _bail_if_private(self._method, self.allow_private)
        if isinstance(self._target, StrictMock):
            template_value = getattr(self._target._template, self._method, None)
            if template_value and callable(template_value):
                if not coroutine_function and asyncio.iscoroutinefunction(
                    template_value
                ):
                    raise ValueError(
                        f"{name}() can not be used with coroutine functions.\n"
                        f"The attribute '{self._method}' of the template class "
                        f"of {self._target} is a coroutine function. You can "
                        f"use {other_name}() instead."
                    )
                if coroutine_function and not (
                    _is_coroutinefunction(template_value) or callable_returns_coroutine
                ):
                    raise ValueError(
                        f"{name}() can not be used with non coroutine "
                        "functions.\n"
                        f"The attribute '{self._method}' of the template class "
                        f"of {self._target} is not a coroutine function. You "
                        f"can use {other_name}() instead."
                    )
        else:
            if inspect.isclass(self._target) and _is_instance_method(
                self._target, self._method
            ):
                raise ValueError(
                    "Patching an instance method at the class is not supported: "
                    "bugs are easy to introduce, as patch is not scoped for an "
                    "instance, which can potentially even break class behavior; "
                    "assertions on calls are ambiguous (for every instance or one "
                    "global assertion?)."
                )
            original_callable = getattr(self._target, self._method)
            if not callable(original_callable):
                raise ValueError(
                    f"{name}() can only be used with callable attributes and "
                    f"{repr(original_callable)} is not."
                )
            if inspect.isclass(original_callable):
                raise ValueError(
                    f"{name}() can not be used with with classes: "
                    f"{repr(original_callable)}. Perhaps you want to use "
                    "mock_constructor() instead."
                )
            if not coroutine_function and asyncio.iscoroutinefunction(
                original_callable
            ):
                raise ValueError(
                    f"{name}() can not be used with coroutine functions.\n"
                    f"{original_callable} is a coroutine function. You can use "
                    f"{other_name}() instead."
                )
            if coroutine_function and not (
                _is_coroutinefunction(original_callable) or callable_returns_coroutine
            ):
                raise ValueError(
                    f"{name}() can not be used with non coroutine functions.\n"
                    f"{original_callable} is not a coroutine function. You can "
                    f"use {other_name}() instead."
                )

    def _patch(
        self, new_value: Union[Callable, _CallableMock]
    ) -> Union[Tuple[Callable, Callable], Tuple[Mock, Callable], Tuple[None, Callable]]:
        self._validate_patch()

        if isinstance(self._target, StrictMock):
            original_callable = None
        else:
            original_callable = getattr(self._target, self._method)

        new_value = _wrap_signature_and_type_validation(
            new_value,
            self._target,
            self._method,
            self.type_validation or self.type_validation is None,
        )

        restore = self._method in self._target.__dict__
        restore_value = self._target.__dict__.get(self._method, None)

        if inspect.isclass(self._target):
            new_value = staticmethod(new_value)  # type: ignore

        unpatcher = _patch(
            self._target, self._method, new_value, restore, restore_value
        )

        return original_callable, unpatcher

    def _get_callable_mock(self) -> _CallableMock:
        return _CallableMock(
            self._original_target,
            self._method,
            self.caller_frame_info,
            type_validation=self.type_validation,
        )

    def __init__(
        self,
        target: Any,
        method: str,
        caller_frame_info: Traceback,
        callable_mock: Union[Callable[[Type[object]], Any], _CallableMock, None] = None,
        original_callable: Optional[Callable] = None,
        allow_private: bool = False,
        type_validation: Optional[bool] = None,
    ) -> None:
        if not _is_setup():
            raise RuntimeError(
                "TestSlide was not correctly setup before usage!\n"
                "This error happens when mock_callable, mock_async_callable or "
                "mock_constructor are attempted to be used without correct "
                "test framework integration, meaning unpatching and "
                "assertions will not work as expected.\n"
                "A common scenario for this is when testslide.TestCase is "
                "subclassed with setUp() overridden but super().setUp() was not "
                "called."
            )
        self._original_target = target
        self._method = method
        self._runner: Optional[_BaseRunner] = None
        self._next_runner_accepted_args: Any = None
        self.allow_private = allow_private
        self.type_validation = type_validation
        self.caller_frame_info = caller_frame_info
        self._allow_coro = False
        if isinstance(target, str):
            self._target = testslide._importer(target)
        else:
            self._target = target

        target_method_id = (id(self._target), method)

        if target_method_id not in self.CALLABLE_MOCKS:
            if not callable_mock:
                patch = True
                callable_mock = self._get_callable_mock()
            else:
                patch = False
            self.CALLABLE_MOCKS[target_method_id] = callable_mock
            self._callable_mock = callable_mock

            def del_callable_mock() -> None:
                del self.CALLABLE_MOCKS[target_method_id]

            _unpatchers.append(del_callable_mock)

            if patch:
                original_callable, unpatcher = self._patch(callable_mock)
                _unpatchers.append(unpatcher)
            self._original_callable = original_callable
            callable_mock.original_callable = original_callable  # type: ignore
        else:
            self._callable_mock = self.CALLABLE_MOCKS[target_method_id]
            self._original_callable = self._callable_mock.original_callable  # type: ignore

    def _add_runner(self, runner: _BaseRunner) -> None:
        if self._runner:
            raise ValueError(
                "Can't define more than one behavior using the same "
                "self.mock_callable() chain. Please call self.mock_callable() again "
                "one time for each new behavior."
            )
        if self._next_runner_accepted_args:
            args, kwargs = self._next_runner_accepted_args
            self._next_runner_accepted_args = None
            runner.add_accepted_args(*args, **kwargs)
        self._runner = runner
        self._callable_mock.runners.insert(0, runner)  # type: ignore

    def _assert_runner(self) -> None:
        if not self._runner:
            raise ValueError(
                "You must first define a behavior. Eg: "
                "self.mock_callable(target, 'func')"
                ".to_return_value(value)"
                ".and_assert_called_exactly(times)"
            )
        if self._runner._call_count > 0:
            raise ValueError(
                f"No extra configuration is allowed after {self._NAME} "
                f"receives its first call, it received {self._runner._call_count} "
                f"call{'s' if self._runner._call_count > 1 else ''} already. "
                "You should instead define it all at once, "
                f"eg: self.{self._NAME}(target, 'func')"
                ".to_return_value(value).and_assert_called_once()"
            )

    ##
    ## Arguments
    ##

    def for_call(
        self, *args: Any, **kwargs: Any
    ) -> Union["_MockCallableDSL", "_MockAsyncCallableDSL", "_MockConstructorDSL"]:
        """
        Filter for only calls like this.
        """
        if self._runner:
            self._runner.add_accepted_args(*args, **kwargs)
        else:
            self._next_runner_accepted_args = (args, kwargs)
        return self

    ##
    ## Behavior
    ##

    def to_return_value(
        self, value: Any
    ) -> Union["_MockCallableDSL", "_MockAsyncCallableDSL", "_MockConstructorDSL"]:
        """
        Always return given value.
        """
        self._add_runner(
            _ReturnValueRunner(
                self._original_target,
                self._method,
                self._original_callable,  # type: ignore
                value,
                self._allow_coro,
            )
        )
        return self

    def to_return_values(
        self, values_list: List[Any]
    ) -> Union["_MockCallableDSL", "_MockAsyncCallableDSL", "_MockConstructorDSL"]:
        """
        For each call, return each value from given list in order.
        When list is exhausted, goes to the next behavior set.
        """
        if not isinstance(values_list, list):
            raise ValueError("{} is not a list".format(values_list))
        self._add_runner(
            _ReturnValuesRunner(
                self._original_target,
                self._method,
                self._original_callable,  # type: ignore
                values_list,
                self._allow_coro,
            )
        )
        return self

    def to_yield_values(
        self, values_list: List[Any]
    ) -> Union["_MockCallableDSL", "_MockAsyncCallableDSL", "_MockConstructorDSL"]:
        """
        Callable will return an iterator what will yield each value from the
        given list.
        """
        if not isinstance(values_list, list):
            raise ValueError("{} is not a list".format(values_list))
        self._add_runner(
            _YieldValuesRunner(
                self._original_target,
                self._method,
                self._original_callable,  # type: ignore
                values_list,
                self._allow_coro,
            )
        )
        return self

    def to_raise(
        self, ex: Union[Type[BaseException], BaseException]
    ) -> Union["_MockCallableDSL", "_MockAsyncCallableDSL", "_MockConstructorDSL"]:
        """
        Raises given exception class or exception instance.
        """
        if isinstance(ex, BaseException):
            self._add_runner(
                _RaiseRunner(
                    self._original_target, self._method, self._original_callable, ex  # type: ignore
                )
            )
        elif isinstance(ex(), BaseException):
            self._add_runner(
                _RaiseRunner(
                    self._original_target, self._method, self._original_callable, ex()  # type: ignore
                )
            )
        else:
            raise ValueError(
                "{} is not subclass or instance of BaseException".format(ex)
            )
        return self

    def with_implementation(
        self, func: Callable
    ) -> Union["_MockCallableDSL", "_MockAsyncCallableDSL", "_MockConstructorDSL"]:
        """
        Replace callable by given function.
        """
        if not callable(func):
            raise ValueError("{} must be callable.".format(func))
        self._add_runner(
            _ImplementationRunner(
                self._original_target,
                self._method,
                self._original_callable,  # type: ignore
                func,
                self._allow_coro,
            )
        )
        return self

    def with_wrapper(
        self, func: Callable
    ) -> Union["_MockCallableDSL", "_MockAsyncCallableDSL", "_MockConstructorDSL"]:
        """
        Replace callable with given wrapper function, that will be called as:

          func(original_func, *args, **kwargs)

        receiving the original function as the first argument as well as any given
        arguments.
        """
        if not callable(func):
            raise ValueError("{} must be callable.".format(func))

        if not self._original_callable:
            raise ValueError("Can not wrap original callable that does not exist.")

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return func(self._original_callable, *args, **kwargs)

        self._add_runner(
            _ImplementationRunner(
                self._original_target,
                self._method,
                self._original_callable,
                wrapper,
                self._allow_coro,
            )
        )
        return self

    def to_call_original(
        self,
    ) -> Union["_MockCallableDSL", "_MockAsyncCallableDSL", "_MockConstructorDSL"]:
        """
        Calls the original callable implementation, instead of mocking it. This is
        useful for example, if you want to by default call the original implementation,
        but for a specific calls, mock the result.
        """
        if not self._original_callable:
            raise ValueError("Can not call original callable that does not exist.")
        self._add_runner(
            _CallOriginalRunner(
                self._original_target, self._method, self._original_callable
            )
        )
        return self

    ##
    ## Call Assertions
    ##

    def and_assert_called_exactly(
        self, count: int
    ) -> Union["_MockCallableDSL", "_MockAsyncCallableDSL", "_MockConstructorDSL"]:
        """
        Assert that there were exactly the given number of calls.

        If assertion is for 0 calls, any received call will raise
        UnexpectedCallReceived and also an AssertionError.
        """
        if count:
            self._assert_runner()
        else:
            if not self._runner:
                self.to_raise(
                    UnexpectedCallReceived(
                        ("{}, {}: Expected not to be called!").format(
                            _format_target(self._target), repr(self._method)
                        )
                    )
                )
        self._runner.add_exact_calls_assertion(count)  # type: ignore
        return self

    def and_assert_not_called(
        self,
    ) -> Union["_MockCallableDSL", "_MockAsyncCallableDSL", "_MockConstructorDSL"]:
        """
        Short for and_assert_called_exactly(0)
        """
        return self.and_assert_called_exactly(0)

    def and_assert_called_once(
        self,
    ) -> Union["_MockCallableDSL", "_MockAsyncCallableDSL", "_MockConstructorDSL"]:
        """
        Short for and_assert_called_exactly(1)
        """
        return self.and_assert_called_exactly(1)

    def and_assert_called_twice(
        self,
    ) -> Union["_MockCallableDSL", "_MockAsyncCallableDSL", "_MockConstructorDSL"]:
        """
        Short for and_assert_called_exactly(2)
        """
        return self.and_assert_called_exactly(2)

    def and_assert_called_at_least(
        self, count: int
    ) -> Union["_MockCallableDSL", "_MockAsyncCallableDSL", "_MockConstructorDSL"]:
        """
        Assert that there at least the given number of calls.
        """
        if count < 1:
            raise ValueError("times must be >= 1")
        self._assert_runner()
        self._runner.add_at_least_calls_assertion(count)  # type: ignore
        return self

    def and_assert_called_at_most(
        self, count: int
    ) -> Union["_MockCallableDSL", "_MockAsyncCallableDSL", "_MockConstructorDSL"]:
        """
        Assert that there at most the given number of calls.
        """
        if count < 1:
            raise ValueError("times must be >= 1")
        self._assert_runner()
        self._runner.add_at_most_calls_assertion(count)  # type: ignore
        return self

    def and_assert_called(
        self,
    ) -> Union["_MockCallableDSL", "_MockAsyncCallableDSL", "_MockConstructorDSL"]:
        """
        Short for self.and_assert_called_at_least(1).
        """
        return self.and_assert_called_at_least(1)

    def and_assert_called_ordered(
        self,
    ) -> Union["_MockCallableDSL", "_MockAsyncCallableDSL", "_MockConstructorDSL"]:
        """
        Assert that multiple calls, potentially to different mock_callable()
        targets, happened in the order defined.
        """
        self._assert_runner()
        self._runner.add_call_order_assertion()  # type: ignore
        return self


class _MockAsyncCallableDSL(_MockCallableDSL):

    _NAME: str = "mock_async_callable"

    def __init__(
        self,
        target: Union[str, type],
        method: str,
        caller_frame_info: Traceback,
        callable_returns_coroutine: bool,
        allow_private: bool = False,
        type_validation: bool = True,
    ) -> None:
        self._callable_returns_coroutine = callable_returns_coroutine
        super().__init__(
            target,
            method,
            caller_frame_info,
            allow_private=allow_private,
            type_validation=type_validation,
        )
        self._allow_coro = True

    def _validate_patch(self) -> None:  # type: ignore
        return super()._validate_patch(
            name=self._NAME,
            other_name="mock_callable",
            coroutine_function=True,
            callable_returns_coroutine=self._callable_returns_coroutine,
        )

    def _get_callable_mock(self) -> _CallableMock:
        return _CallableMock(
            self._original_target,
            self._method,
            self.caller_frame_info,
            is_async=True,
            type_validation=self.type_validation,
        )

    def with_implementation(self, func: Callable) -> "_MockAsyncCallableDSL":
        """
        Replace callable by given async function.
        """
        if not callable(func):
            raise ValueError("{} must be callable.".format(func))
        self._add_runner(
            _AsyncImplementationRunner(
                self._original_target, self._method, self._original_callable, func  # type: ignore
            )
        )
        return self

    def with_wrapper(self, func: Callable) -> "_MockAsyncCallableDSL":
        """
        Replace callable with given wrapper async function, that will be called as:

          await func(original_async_func, *args, **kwargs)

        receiving the original function as the first argument as well as any given
        arguments.
        """
        if not callable(func):
            raise ValueError("{} must be callable.".format(func))

        if not self._original_callable:
            raise ValueError("Can not wrap original callable that does not exist.")

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            coro = func(self._original_callable, *args, **kwargs)
            if not _is_coroutine(coro):
                raise NotACoroutine(
                    f"Function did not return a coroutine.\n"
                    f"{func} must return a coroutine."
                )
            return await coro

        self._add_runner(
            _AsyncImplementationRunner(
                self._original_target, self._method, self._original_callable, wrapper
            )
        )
        return self

    def to_call_original(self) -> "_MockAsyncCallableDSL":
        """
        Calls the original callable implementation, instead of mocking it. This is
        useful for example, if you want to by default call the original implementation,
        but for a specific calls, mock the result.
        """
        if not self._original_callable:
            raise ValueError("Can not call original callable that does not exist.")
        self._add_runner(
            _AsyncCallOriginalRunner(
                self._original_target, self._method, self._original_callable
            )
        )
        return self
