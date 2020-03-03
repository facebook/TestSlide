#!/usr/bin/env python3
# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import inspect
import typeguard
import typing


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


# FullArgSpec(args=['a', 'b', 'c', 'd', 'e', 'f', 'g'], varargs=None, varkw=None, defaults=None, kwonlyargs=[], kwonlydefaults=None, annotations={'a': <class 'int'>, 'b': <class 'float'>, 'c': <class 'dict'>, 'd': <class 'list'>})
def _validate_function_signature(argspec: inspect.FullArgSpec, args, kwargs):
    type_errs = []
    for idx in range(0, len(args)):
        if argspec.args:
            arg = argspec.args[idx]
            try:
                __validate_argument_type(argspec.annotations, arg, args[idx])
            except TypeError as te:
                type_errs.append(te)
    for k, v in kwargs.items():
        try:
            __validate_argument_type(argspec.annotations, k, v)
        except TypeError as te:
            type_errs.append(te)
    return type_errs


def __validate_argument_type(annotations, argname, value):
    type_information = annotations.get(argname)
    if type_information:
        typeguard.check_type(argname, value, type_information)
