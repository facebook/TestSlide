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


def _validate_argument_type(
    annotations: Dict[str, Any], argname: str, value: Any
) -> None:
    type_information = annotations.get(argname)
    if not type_information:
        return

    if _is_a_mock(value):
        template = _extract_mock_template(value)
        if template:
            value = template
        else:
            return

    typeguard.check_type(argname, value, type_information)


def _validate_function_signature(
    callable_template: Callable, args: Tuple[Any], kwargs: Dict[str, Any]
):
    argspec = inspect.getfullargspec(callable_template)
    try:
        signature = inspect.signature(callable_template)
    except ValueError:
        signature = None
    type_errors = []
    for idx in range(0, len(args)):
        if argspec.args:
            # We use the signature whenever available because for class methods
            # argspec has the extra 'cls' value
            if signature:
                argname = list(signature.parameters.keys())[idx]
            else:
                argname = argspec.args[idx]
            try:
                _validate_argument_type(argspec.annotations, argname, args[idx])
            except TypeError as type_error:
                type_errors.append(f"{repr(argname)}: {type_error}")
    for argname, value in kwargs.items():
        try:
            _validate_argument_type(argspec.annotations, argname, value)
        except TypeError as type_error:
            type_errors.append(f"{repr(argname)}: {type_error}")
    if type_errors:
        raise TypeError(
            "Call with incompatible argument types:\n  " + "\n  ".join(type_errors)
        )


def _wrap_signature_and_type_validation(value, template, attr_name):
    if _is_a_mock(template):
        template = _extract_mock_template(template)
        if not template:
            return value

    # This covers runtime attributes
    if not hasattr(template, attr_name):
        return value

    callable_template = getattr(template, attr_name)

    # FIXME decouple from _must_skip. It tells when self should be skipped
    # for signature validation.
    if unittest.mock._must_skip(template, attr_name, isinstance(template, type)):
        callable_template = functools.partial(callable_template, None)

    try:
        signature = inspect.signature(callable_template, follow_wrapped=False)
    except ValueError:
        signature = None

    def with_sig_check(*args, **kwargs):
        if signature:
            try:
                signature.bind(*args, **kwargs)
            except TypeError as e:
                raise TypeError(
                    "{}, {}: {}".format(repr(template), repr(attr_name), str(e))
                )
            _validate_function_signature(callable_template, args, kwargs)
        return value(*args, **kwargs)

    return with_sig_check


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
