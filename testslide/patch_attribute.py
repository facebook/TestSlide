# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from typing import Any, Callable, Dict, Tuple

import testslide
from testslide.strict_mock import UndefinedAttribute

from .lib import _bail_if_private, _validate_argument_type
from .patch import _patch

_restore_values: Dict[Tuple[Any, str], Any] = {}
_unpatchers: Dict[Tuple[Any, str], Callable] = {}


def unpatch_all_mocked_attributes() -> None:
    """
    This method must be called after every test unconditionally to remove all
    active patch_attribute() patches.
    """
    unpatch_exceptions = []
    for unpatcher in _unpatchers.values():
        try:
            unpatcher()
        except Exception as e:
            unpatch_exceptions.append(e)
    _restore_values.clear()
    _unpatchers.clear()
    if unpatch_exceptions:
        raise RuntimeError(
            "Exceptions raised when unpatching: {}".format(unpatch_exceptions)
        )


def patch_attribute(
    target: Any,
    attribute: str,
    new_value: Any,
    allow_private: bool = False,
    type_validation: bool = True,
) -> None:
    """
    Patch target's attribute with new_value. The target can be any Python
    object, such as modules, classes or instances; attribute is a string with
    the attribute name and new_value.. is the value to be patched.

    patch_attribute() has special mechanics so it "just works" for all cases.

    For example, patching a @property at an instance requires changes in the
    class, which may affect other instances. patch_attribute() takes care of
    what's needed, so only the target instance is affected.
    """
    _bail_if_private(attribute, allow_private)

    if isinstance(target, str):
        target = testslide._importer(target)

    key = (id(target), attribute)

    if isinstance(target, testslide.StrictMock):
        if not type_validation:
            target.__dict__["_attributes_to_skip_type_validation"].append(attribute)
        template_class = target._template
        if template_class and attribute not in target._runtime_attrs:
            value = getattr(template_class, attribute)
            if not isinstance(value, type) and callable(value):
                raise ValueError(
                    "Attribute can not be callable!\n"
                    "You can either use mock_callable() / mock_async_callable() instead."
                )

        def strict_mock_hasattr(obj: object, name: str) -> bool:
            try:
                return hasattr(obj, name)
            except UndefinedAttribute:
                return False

        if strict_mock_hasattr(target, attribute) and key not in _unpatchers:
            restore = True
            restore_value = getattr(target, attribute)
        else:
            restore = False
            restore_value = None
        skip_unpatcher = False
    else:
        if key in _unpatchers:
            restore = False
            restore_value = _restore_values[key]
            skip_unpatcher = True
        else:
            restore = True
            restore_value = getattr(target, attribute)
            skip_unpatcher = False
        if isinstance(restore_value, type):
            raise ValueError(
                "Attribute can not be a class!\n"
                "You can use mock_constructor() instead."
            )
        if callable(restore_value):
            raise ValueError(
                "Attribute can not be callable!\n"
                "You can either use mock_callable() / mock_async_callable() instead."
            )
        if type_validation:
            _validate_argument_type(type(restore_value), attribute, new_value)

    if restore:
        _restore_values[key] = restore_value

    unpatcher = _patch(target, attribute, new_value, restore, restore_value)

    if not skip_unpatcher:
        _unpatchers[key] = unpatcher
