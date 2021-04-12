# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.
import functools
import inspect
import os
import sys
import unittest.mock
from functools import wraps
from inspect import Traceback
from types import FrameType
from typing import TYPE_CHECKING, Any, Callable, Dict, Optional, Tuple, Type, Union
from unittest.mock import Mock

import typeguard

if TYPE_CHECKING:
    # hack to remove mypy warnings about types not being defined
    from testslide.mock_callable import _CallableMock
    from testslide.strict_mock import StrictMock, _DefaultMagic

##
## Type validation
##


class TypeCheckError(BaseException):
    """
    Raised when bad typing is detected during runtime. It inherits from
    BaseException to prevent the exception being caught and hidden by the code
    being tested, letting it surface to the test runner.
    """

    pass


class CoroutineValueError(BaseException):
    def __init__(self) -> None:
        self.message = "Setting coroutines as return value is not allowed. Use mock_async_callable instead, or use callable_returns_coroutine=True "

    def __str__(self) -> str:
        return self.message


class WrappedMock(unittest.mock.NonCallableMock):
    """Needed to be able to show the useful qualified name for mock specs"""

    def get_qualified_name(self) -> str:
        return typeguard.qualified_name(self._spec_class)


def _extract_NonCallableMock_template(mock_obj: Mock) -> Optional[Any]:
    if "_spec_class" in mock_obj.__dict__ and mock_obj._spec_class is not None:
        return mock_obj._spec_class

    return None


MOCK_TEMPLATE_EXTRACTORS: Dict[Type, Callable[[Mock], Optional[Any]]] = {
    unittest.mock.NonCallableMock: _extract_NonCallableMock_template
}


def _extract_mock_template(
    mock: Union[Mock, "StrictMock"]
) -> Optional[Union[Type[str], Type[dict], Type[int]]]:
    template = None
    for mock_class, extract_mock_template in MOCK_TEMPLATE_EXTRACTORS.items():
        if isinstance(mock, mock_class):
            template = extract_mock_template(mock)
    return template


def _is_a_mock(maybe_mock: Any) -> bool:
    return any(
        isinstance(maybe_mock, mock_class)
        for mock_class in MOCK_TEMPLATE_EXTRACTORS.keys()
    )


def _is_a_builtin(obj: Any) -> bool:
    # Builtins have historically had terrible inspectability.
    # In Cython 0.29 signature methods just raised ValueError
    # In Cython 3.0 signature methods return a signature that is missing default value
    # information, thinking all arguments are required
    return (
        type(obj) is type(list.append)
        # Cython 3.0 changed to not be a "method_descriptor"
        or type(obj).__name__ == "cython_function_or_method"
    )


def _get_caller_vars() -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Retrieves the globals and locals of the first frame that is not from TestSlide code.
    """

    def _should_skip_frame(frame: FrameType) -> bool:
        is_testslide = (
            os.path.dirname(__file__) in frame.f_code.co_filename
            # we need not to skip tests
            and "/tests/" not in frame.f_code.co_filename
        )
        is_typeguard = os.path.dirname(typeguard.__file__) in frame.f_code.co_filename

        return is_testslide or is_typeguard

    next_stack_count = 1
    next_frame = sys._getframe(next_stack_count)
    while _should_skip_frame(next_frame):
        next_stack_count += 1
        next_frame = sys._getframe(next_stack_count)

    return (next_frame.f_globals, next_frame.f_locals)


def _validate_callable_signature(
    skip_first_arg: bool,
    callable_template: Callable,
    template: Any,
    attr_name: str,
    args: Any,
    kwargs: Dict[str, Any],
) -> bool:
    # python stdlib tests have to exempt some builtins for signature validation tests
    # they use a giant alloy/deny list, which is impractical here so just ignore
    # all builtins.
    if _is_a_builtin(callable_template):
        return False
    if skip_first_arg and not inspect.ismethod(callable_template):
        callable_template = functools.partial(callable_template, None)
    try:
        signature = inspect.signature(callable_template, follow_wrapped=False)
    except ValueError:
        return False

    try:
        signature.bind(*args, **kwargs)
    except TypeError as e:
        raise TypeError("{}, {}: {}".format(repr(template), repr(attr_name), str(e)))
    return True


def _validate_argument_type(expected_type: Type, name: str, value: Any) -> None:
    if "~" in str(expected_type):
        # this means that we have a TypeVar type, and those require
        # checking all the types of all the params as a whole, but we
        # don't have a good way of getting right now
        # TODO: #165
        return

    original_check_type = typeguard.check_type
    original_qualified_name = typeguard.qualified_name

    def wrapped_qualified_name(obj: object) -> str:
        """Needed to be able to show the useful qualified name for mock specs"""
        if isinstance(obj, WrappedMock):
            return obj.get_qualified_name()

        return original_qualified_name(obj)

    def wrapped_check_type(
        argname: str,
        inner_value: Any,
        inner_expected_type: Type,
        *args: Any,
        globals: Optional[Dict[str, Any]] = None,
        locals: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:

        if _is_a_mock(inner_value):
            inner_type = _extract_mock_template(inner_value)
            if inner_type is None:
                return

            # Ugly hack to make mock objects not be subclass of Mock
            inner_value = WrappedMock(spec=inner_type)

        # typeguard only checks the previous caller stack, so in order to be
        # able to do forward type references we have to extract the caller
        # stack ourselves.
        if kwargs.get("memo") is None and globals is None and locals is None:
            globals, locals = _get_caller_vars()

        return original_check_type(
            argname,
            inner_value,
            inner_expected_type,
            *args,
            globals=globals,
            locals=locals,
            **kwargs,
        )

    with unittest.mock.patch.object(
        typeguard, "check_type", new=wrapped_check_type
    ), unittest.mock.patch.object(
        typeguard, "qualified_name", new=wrapped_qualified_name
    ):
        try:
            typeguard.check_type(name, value, expected_type)
        except TypeError as type_error:
            raise TypeCheckError(str(type_error))


def _validate_callable_arg_types(
    skip_first_arg: bool,
    callable_template: Callable,
    args: Any,
    kwargs: Dict[str, Any],
) -> None:
    argspec = inspect.getfullargspec(callable_template)
    idx_offset = 1 if skip_first_arg else 0
    type_errors = []
    for idx in range(0, len(args)):
        if argspec.args:
            if idx + idx_offset >= len(argspec.args):
                if argspec.varargs:
                    continue
                raise TypeError("Extra argument given: ", repr(args[idx]))
            argname = argspec.args[idx + idx_offset]
            try:
                expected_type = argspec.annotations.get(argname)
                if not expected_type:
                    continue

                _validate_argument_type(expected_type, argname, args[idx])
            except TypeCheckError as type_error:
                type_errors.append(f"{repr(argname)}: {type_error}")

    for argname, value in kwargs.items():
        try:
            expected_type = argspec.annotations.get(argname)
            if not expected_type:
                continue

            _validate_argument_type(expected_type, argname, value)
        except TypeCheckError as type_error:
            type_errors.append(f"{repr(argname)}: {type_error}")

    if type_errors:
        raise TypeCheckError(
            "Call to "
            + callable_template.__name__
            + " has incompatible argument types:\n  "
            + "\n  ".join(type_errors)
        )


def _skip_first_arg(template: Any, attr_name: str) -> bool:

    if inspect.ismodule(template):
        return False

    if inspect.isclass(template):
        mro = template.__mro__
    else:
        mro = template.__class__.__mro__

    for klass in mro:
        if attr_name not in klass.__dict__:
            continue
        attr = klass.__dict__[attr_name]
        if isinstance(attr, classmethod):
            return True
        elif isinstance(attr, staticmethod):
            return False
        else:
            return True

    return False


def _wrap_signature_and_type_validation(
    value: Union["_DefaultMagic", Callable, "_CallableMock"],
    template: Any,
    attr_name: str,
    type_validation: bool,
) -> Union[Callable, "_CallableMock"]:
    if _is_a_mock(template):
        template = _extract_mock_template(template)
        if not template:
            return value

    # This covers runtime attributes
    if not hasattr(template, attr_name):
        return value

    callable_template = getattr(template, attr_name)

    skip_first_arg = _skip_first_arg(template, attr_name)

    # Add this so docstrings and method name are not altered by the mock
    @wraps(callable_template)
    def with_sig_and_type_validation(*args: Any, **kwargs: Any) -> Any:
        if _validate_callable_signature(
            skip_first_arg, callable_template, template, attr_name, args, kwargs
        ):
            if type_validation:
                _validate_callable_arg_types(
                    skip_first_arg, callable_template, args, kwargs
                )
        return value(*args, **kwargs)

    # Update __qualname__ such that `repr(mocked_function)` would look like
    # `<function TestSldeValidation(<original_name>) at 0x105c17560>`
    with_sig_and_type_validation.__qualname__ = "TestSldeValidation({})".format(
        with_sig_and_type_validation.__qualname__
    )
    setattr(  # noqa: B010
        with_sig_and_type_validation, "__is_testslide_type_validation_wrapping", True
    )
    return with_sig_and_type_validation


def _is_wrapped_for_signature_and_type_validation(value: Callable) -> bool:
    return getattr(value, "__is_testslide_type_validation_wrapping", False)


def _validate_return_type(
    template: Union[Mock, Callable], value: Any, caller_frame_info: Traceback
) -> None:
    try:
        argspec = inspect.getfullargspec(template)
    except TypeError:
        return
    expected_type = argspec.annotations.get("return")
    if expected_type:
        try:
            _validate_argument_type(expected_type, "return", value)
        except TypeCheckError as runtime_type_error:
            raise TypeCheckError(
                f"{str(runtime_type_error)}: {repr(value)}\n"
                f"Defined at {caller_frame_info.filename}:"
                f"{caller_frame_info.lineno}"
            )


##
## Private attributes
##


def _bail_if_private(candidate: str, allow_private: bool) -> None:
    if (
        candidate.startswith("_")
        and not allow_private
        and not (candidate.startswith("__") and candidate.endswith("__"))
    ):
        raise ValueError(
            "It's disencouraged to patch/mock private interfaces.\n"
            "This would result in way too coupled tests and implementation. "
            "Please consider using patterns like dependency injection instead. "
            "If you really need to do this use the allow_private=True argument."
        )
