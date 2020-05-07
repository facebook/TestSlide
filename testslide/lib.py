#!/usr/bin/env python3
# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.
import inspect
import functools
import typeguard
from typing import Any, Callable, Dict, Optional, Type, Tuple

import unittest.mock

##
## Type validation
##


def _extract_NonCallableMock_template(mock_obj) -> Optional[Any]:
    if "_spec_class" in mock_obj.__dict__ and mock_obj._spec_class is not None:
        return mock_obj._spec_class

    return None


MOCK_TEMPLATE_EXTRACTORS: Dict[Type, Callable[[Type], Optional[Any]]] = {
    unittest.mock.NonCallableMock: _extract_NonCallableMock_template
}


def _extract_mock_template(mock):
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


def _validate_callable_signature(
    skip_first_arg, callable_template, template, attr_name, args, kwargs
):
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


def _validate_argument_type(expected_type, name: str, value) -> None:
    if "~" in str(expected_type):
        # this means that we have a TypeVar type, and those require
        # checking all the types of all the params as a whole, but we
        # don't have a good way of getting right now
        # TODO: #165
        return

    original_check_type = typeguard.check_type

    def wrapped_check_type(argname, inner_value, inner_expected_type, *args, **kwargs):
        if _is_a_mock(inner_value):
            if _extract_mock_template(inner_value) is None:
                return
        return original_check_type(
            argname, inner_value, inner_expected_type, *args, **kwargs
        )

    with unittest.mock.patch.object(typeguard, "check_type", new=wrapped_check_type):
        typeguard.check_type(name, value, expected_type)


def _validate_callable_arg_types(
    skip_first_arg,
    callable_template: Callable,
    args: Tuple[Any],
    kwargs: Dict[str, Any],
):
    argspec = inspect.getfullargspec(callable_template)
    idx_offest = 1 if skip_first_arg else 0
    type_errors = []
    for idx in range(0, len(args)):
        if argspec.args:
            if idx + idx_offest >= len(argspec.args):
                if argspec.varargs:
                    continue
                raise TypeError("Extra argument given: ", repr(args[idx]))
            argname = argspec.args[idx + idx_offest]
            try:
                expected_type = argspec.annotations.get(argname)
                if not expected_type:
                    continue

                _validate_argument_type(expected_type, argname, args[idx])
            except TypeError as type_error:
                type_errors.append(f"{repr(argname)}: {type_error}")

    for argname, value in kwargs.items():
        try:
            expected_type = argspec.annotations.get(argname)
            if not expected_type:
                continue

            _validate_argument_type(expected_type, argname, value)
        except TypeError as type_error:
            type_errors.append(f"{repr(argname)}: {type_error}")

    if type_errors:
        raise TypeError(
            "Call with incompatible argument types:\n  " + "\n  ".join(type_errors)
        )


def _skip_first_arg(template, attr_name):

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


def _wrap_signature_and_type_validation(value, template, attr_name, type_validation):
    if _is_a_mock(template):
        template = _extract_mock_template(template)
        if not template:
            return value

    # This covers runtime attributes
    if not hasattr(template, attr_name):
        return value

    callable_template = getattr(template, attr_name)

    skip_first_arg = _skip_first_arg(template, attr_name)

    def with_sig_and_type_validation(*args, **kwargs):
        if _validate_callable_signature(
            skip_first_arg, callable_template, template, attr_name, args, kwargs
        ):
            if type_validation:
                _validate_callable_arg_types(
                    skip_first_arg, callable_template, args, kwargs
                )
        return value(*args, **kwargs)

    return with_sig_and_type_validation


def _validate_return_type(template, value, caller_frame_info):
    try:
        argspec = inspect.getfullargspec(template)
    except TypeError:
        return
    expected_type = argspec.annotations.get("return")
    if expected_type:
        try:
            _validate_argument_type(expected_type, "return", value)
        except TypeError as type_error:
            raise TypeError(
                f"{str(type_error)}: {repr(value)}\n"
                f"Defined at {caller_frame_info.filename}:"
                f"{caller_frame_info.lineno}"
            )


##
## Private attributes
##


def _bail_if_private(candidate: str, allow_private: bool):
    if (
        candidate.startswith("_")
        and not allow_private
        and not (candidate.startswith("__") and candidate.endswith("__"))
    ):
        raise ValueError(
            f"It's disencouraged to patch/mock private interfaces.\n"
            "This would result in way too coupled tests and implementation. "
            "Please consider using patterns like dependency injection instead. "
            "If you really need to do this use the allow_private=True argument."
        )
