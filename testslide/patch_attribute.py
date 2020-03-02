# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import testslide
from .patch import _patch
from .lib import _bail_if_private
from testslide.strict_mock import UndefinedAttribute

_unpatchers = []


def unpatch_all_mocked_attributes():
    """
    This method must be called after every test unconditionally to remove all
    active patch_attribute() patches.
    """
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


def patch_attribute(target, attribute, new_value, allow_private=False):
    """
    Patch target's attribute with new_value. The target can be any Python
    object, such as modules, classes or instances; attribute is a string with
    the attribute name and new_value.. is the value to be patched.

    patch_attribute() has special mechanics so it "just works" for all cases.

    For example, patching a @property at an instance requires changes in the
    class, which may affect other instances. patch_attribute() takes care of
    what's needed, so only the target instance is affected.
    """
    if isinstance(target, str):
        target = testslide._importer(target)

    if isinstance(target, testslide.StrictMock):
        template_class = target._template
        if template_class:
            value = getattr(template_class, attribute)
            if not isinstance(value, type) and callable(value):
                raise ValueError(
                    "Attribute can not be callable!\n"
                    "You can either use mock_callable() / mock_async_callable() instead."
                )

        def sm_hasattr(obj, name):
            try:
                return hasattr(obj, name)
            except UndefinedAttribute:
                return False

        if sm_hasattr(target, attribute):
            restore = True
            restore_value = getattr(target, attribute)
        else:
            restore = False
            restore_value = None
    else:
        restore = True
        restore_value = getattr(target, attribute)
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
    _bail_if_private(attribute, allow_private)
    unpatcher = _patch(target, attribute, new_value, restore, restore_value)
    _unpatchers.append(unpatcher)
