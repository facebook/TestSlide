#!/usr/bin/env python3
# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.
import inspect
import typeguard
from typing import Any, Callable, Dict, Iterable, List, Optional, Type


def _unwrap_mock(
    maybe_mock: Any, mock_extractors: Dict[Type, Callable]
) -> Optional[Any]:
    unwrap_func = next(
        (
            unwrap_func
            for mock_class, unwrap_func in mock_extractors.items()
            if isinstance(maybe_mock, mock_class)
        ),
        lambda x: x,
    )

    return unwrap_func(maybe_mock)


def validate_function_signature(
    argspec: inspect.FullArgSpec, args, kwargs, mock_extractors: Dict[Type, Callable]
) -> List[TypeError]:
    type_errs = []
    for idx in range(0, len(args)):
        if argspec.args:
            arg = argspec.args[idx]
            try:
                __validate_argument_type(
                    argspec.annotations, arg, args[idx], mock_extractors
                )
            except TypeError as te:
                type_errs.append(te)
    for k, v in kwargs.items():
        try:
            __validate_argument_type(argspec.annotations, k, v, mock_extractors)
        except TypeError as te:
            type_errs.append(te)
    return type_errs


def _is_a_mock(maybe_mock: Any, mock_classes: Iterable[Type]) -> bool:
    return any(isinstance(maybe_mock, mock_class) for mock_class in mock_classes)


def __validate_argument_type(
    annotations: Dict[str, Any],
    argname: str,
    value: Any,
    mock_extractors: Dict[Type, Callable],
) -> None:
    type_information = annotations.get(argname)
    if type_information:
        unwrapped_value = _unwrap_mock(value, mock_extractors)
        if _is_a_mock(unwrapped_value, mock_classes=mock_extractors.keys()):
            return
        else:
            typeguard.check_type(argname, value, type_information)


def _bail_if_private(candidate: str, allow_private: False):
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
