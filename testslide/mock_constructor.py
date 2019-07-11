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
import sys

if sys.version_info[0] >= 3:
    import typing

import testslide
from testslide.mock_callable import _MockCallableDSL, _CallableMock

_unpatchers = []
_mocked_classes = {}
_restore_dict = {}
_init_args = None
_init_kwargs = None


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


def _is_string(obj):
    return any(
        string_type
        for string_type in six.string_types
        if issubclass(type(obj), string_type)
    )


class _MockConstructorDSL(_MockCallableDSL):
    """
    Specialized version of _MockCallableDSL to call __new__ with correct args
    """

    def __init__(self, target, method, cls, callable_mock=None, original_callable=None):
        self.cls = cls
        super(_MockConstructorDSL, self).__init__(
            target,
            method,
            callable_mock=callable_mock,
            original_callable=original_callable,
        )

    def for_call(self, *args, **kwargs):
        return super(_MockConstructorDSL, self).for_call(
            *((self.cls,) + args), **kwargs
        )

    def with_wrapper(self, func):
        def new_func(original_callable, cls, *args, **kwargs):
            assert cls == self.cls

            def new_original_callable(*args, **kwargs):
                return original_callable(cls, *args, **kwargs)

            return func(new_original_callable, *args, **kwargs)

        return super(_MockConstructorDSL, self).with_wrapper(new_func)


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
        callable_mock = mocked_class.__new__
    else:
        original_class = getattr(target, class_name)
        if "__new__" in original_class.__dict__:
            raise NotImplementedError(
                "Usage with classes that define __new__() is currently not supported."
            )
        if not inspect.isclass(original_class):
            raise ValueError("Target must be a class.")
        callable_mock = _CallableMock(original_class, "__new__")

        EXCLUDED_ATTRS = ("__new__", "__module__", "__doc__", "__new__")
        _restore_dict[mocked_class_id] = {
            name: value
            for name, value in original_class.__dict__.items()
            if name not in EXCLUDED_ATTRS
        }
        for name in _restore_dict[mocked_class_id].keys():
            if name not in EXCLUDED_ATTRS:
                delattr(original_class, name)

        def new_mock(cls, *args, **kwargs):
            global _init_args
            global _init_kwargs

            assert cls is mocked_class

            _init_args = args
            _init_kwargs = kwargs

            return object.__new__(cls)

        def init_mock(self, *args, **kwargs):
            global _init_args
            global _init_kwargs
            assert _init_args is not None
            assert _init_kwargs is not None
            if "__init__" in _restore_dict[mocked_class_id]:
                init = _restore_dict[mocked_class_id]["__init__"].__get__(
                    self, mocked_class
                )
            else:
                init = original_class.__init__.__get__(self, mocked_class)
            try:
                init(*_init_args, **_init_kwargs)
            finally:
                _init_args = None
                _init_kwargs = None

        mocked_class_dict = {"__new__": callable_mock, "__init__": init_mock}
        mocked_class_dict.update(
            {
                name: value
                for name, value in _restore_dict[mocked_class_id].items()
                if name not in ("__new__", "__init__")
            }
        )

        mocked_class = type(
            str(original_class.__name__) + "Mock", (original_class,), mocked_class_dict
        )

        def unpatcher():
            for name, value in _restore_dict[mocked_class_id].items():
                setattr(original_class, name, value)
            del _restore_dict[mocked_class_id]
            setattr(target, class_name, original_class)
            del _mocked_classes[mocked_class_id]

        _unpatchers.append(unpatcher)

        setattr(target, class_name, mocked_class)
        _mocked_classes[mocked_class_id] = (original_class, mocked_class)

    def original_callable(cls, *args, **kwargs):
        return new_mock(cls, *args, **kwargs)

    return _MockConstructorDSL(
        target=mocked_class,
        method="__new__",
        cls=mocked_class,
        callable_mock=callable_mock,
        original_callable=original_callable,
    )
