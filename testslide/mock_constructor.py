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
_skip_init = []


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
        if not inspect.isclass(original_class):
            raise ValueError("Target must be a class.")

        def unpatcher():
            setattr(target, class_name, original_class)
            del _mocked_classes[mocked_class_id]

        _unpatchers.append(unpatcher)

        callable_mock = _CallableMock(original_class, "__new__")

        if sys.version_info.major >= 3 and sys.version_info.minor >= 6:
            mro = tuple(c for c in original_class.mro()[1:] if c is not typing.Generic)
        else:
            mro = tuple(original_class.mro()[1:])
        mocked_class = type(
            str(original_class.__name__),
            mro,
            {
                name: value
                for name, value in original_class.__dict__.items()
                if name not in ("__new__", "__init__")
            },
        )

        def skip_init(self, *args, **kwargs):
            """
            Avoids __init__ being called automatically with different arguments
            than __new__ after original_callable() returns.
            """
            if id(self) in _skip_init:
                _skip_init.remove(id(self))
                return
            super(type(self), self).__init__(*args, **kwargs)

        mocked_class.__init__ = skip_init

        if "__new__" in original_class.__dict__:
            raise NotImplementedError()
        else:
            mocked_class.__new__ = callable_mock

        setattr(target, class_name, mocked_class)
        _mocked_classes[mocked_class_id] = (original_class, mocked_class)

    def original_callable(cls, *args, **kwargs):
        instance = object.__new__(mocked_class)
        # We call __init__ here so we can ensure it is called with the correct
        # arguments, which might have been mangled by a wrapper function...
        instance.__init__(*args, **kwargs)
        # ...and block the interpreter from calling __init__ again with
        # (potentially with different arguments)
        _skip_init.append(id(instance))
        return instance

    return _MockConstructorDSL(
        target=mocked_class,
        method="__new__",
        cls=mocked_class,
        callable_mock=callable_mock,
        original_callable=original_callable,
    )
