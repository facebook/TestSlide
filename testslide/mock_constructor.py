# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import inspect
import six

if six.PY2:
    from mock import ANY
else:
    from unittest.mock import ANY
import testslide
from testslide.mock_callable import _MockCallableDSL, _CallableMock

_unpatchers = []  # type: List[Callable]  # noqa T484


def unpatch_all_constructor_mocks():
    """
    This method must be called after every test unconditionally to remove all
    active patches.
    """
    try:
        for unpatcher in _unpatchers:
            unpatcher()
    finally:
        del _unpatchers[:]


_mocked_classes = {}


def _is_string(obj):
    return any(
        string_type
        for string_type in six.string_types
        if issubclass(type(obj), string_type)
    )


def mock_constructor(target, class_name):
    if not _is_string(class_name):
        raise ValueError("Second argument must be a string with the name of the class.")
    if _is_string(target):
        target = testslide._importer(target)

    mocked_class_id = (id(target), class_name)

    if mocked_class_id in _mocked_classes:
        original_class, mocked_class = _mocked_classes[mocked_class_id]
        if not getattr(target, class_name) is mocked_class:
            raise AssertionError(
                "The class {} at {} was changed after mock_constructor() mocked "
                "it!".format(class_name, target)
            )
        callable_mock = getattr(mocked_class, "__new__")
    else:

        original_class = getattr(target, class_name)
        if not inspect.isclass(original_class):
            raise ValueError("Target must be a class.")

        def unpatcher():
            setattr(target, class_name, original_class)
            del _mocked_classes[mocked_class_id]

        _unpatchers.append(unpatcher)

        callable_mock = _CallableMock(original_class, "__new__")

        mocked_class = type(
            str(original_class.__name__ + "Mock"),
            (original_class,),
            {"__new__": callable_mock},
        )
        setattr(target, class_name, mocked_class)
        _mocked_classes[mocked_class_id] = (original_class, mocked_class)

    def original_callable(_, *args, **kwargs):
        return original_class(*args, **kwargs)

    return _MockCallableDSL(
        mocked_class,
        "__new__",
        callable_mock=callable_mock,
        original_callable=original_callable,
        prepend_first_arg=ANY,
    )
