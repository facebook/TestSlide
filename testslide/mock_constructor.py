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

import testslide
from testslide.mock_callable import _MockCallableDSL, _CallableMock


_DO_NOT_COPY_CLASS_ATTRIBUTES = (
    "__dict__",
    "__doc__",
    "__module__",
    "__new__",
)


_unpatchers = []
_mocked_classes = {}
_restore_dict = {}
_init_args_from_original_callable = None
_init_kwargs_from_original_callable = None


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


def _get_mocked_class(original_class, mocked_class_id, callable_mock):
    # Extract class attributes from the target class...
    _restore_dict[mocked_class_id] = {}
    class_dict_to_copy = {
        name: value
        for name, value in original_class.__dict__.items()
        if name not in _DO_NOT_COPY_CLASS_ATTRIBUTES
    }
    for name, value in class_dict_to_copy.items():
        try:
            delattr(original_class, name)
        # Safety net against missing items at _DO_NOT_COPY_CLASS_ATTRIBUTES
        except (AttributeError, TypeError):
            pass
        _restore_dict[mocked_class_id][name] = value
    # ...and reuse them...
    mocked_class_dict = {"__new__": callable_mock}
    mocked_class_dict.update(
        {
            name: value
            for name, value in _restore_dict[mocked_class_id].items()
            if name not in ("__new__", "__init__")
        }
    )

    # ...to create the mocked subclass.
    mocked_class = type(
        str(original_class.__name__), (original_class,), mocked_class_dict
    )

    # Because __init__ is called after __new__ unconditionally with the same
    # arguments, we need to mock it fir this first call, to call the real
    # __init__ with the correct arguments.
    def init_with_correct_args(self, *args, **kwargs):
        global _init_args_from_original_callable, _init_kwargs_from_original_callable
        assert _init_args_from_original_callable is not None
        assert _init_kwargs_from_original_callable is not None
        # If __init__ available at the class __dict__...
        if "__init__" in _restore_dict[mocked_class_id]:
            # Use it,
            init = _restore_dict[mocked_class_id]["__init__"].__get__(
                self, mocked_class
            )
        else:
            # otherwise, pull from a parent class.
            init = original_class.__init__.__get__(self, mocked_class)
        try:
            init(
                *_init_args_from_original_callable,
                **_init_kwargs_from_original_callable
            )
        finally:
            _init_args_from_original_callable = None
            _init_kwargs_from_original_callable = None
        # Restore __init__ so subsequent calls can work.
        setattr(mocked_class, "__init__", init)

    mocked_class.__init__ = init_with_correct_args

    return mocked_class


def _patch_and_return_mocked_class(
    target, class_name, mocked_class_id, original_class, callable_mock
):
    mocked_class = _get_mocked_class(original_class, mocked_class_id, callable_mock)

    def unpatcher():
        for name, value in _restore_dict[mocked_class_id].items():
            setattr(original_class, name, value)
        del _restore_dict[mocked_class_id]
        setattr(target, class_name, original_class)
        del _mocked_classes[mocked_class_id]

    _unpatchers.append(unpatcher)

    setattr(target, class_name, mocked_class)
    _mocked_classes[mocked_class_id] = (original_class, mocked_class)

    return mocked_class


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
        mocked_class = _patch_and_return_mocked_class(
            target, class_name, mocked_class_id, original_class, callable_mock
        )

    def original_callable(cls, *args, **kwargs):
        global _init_args_from_original_callable, _init_kwargs_from_original_callable
        assert cls is mocked_class
        # Python unconditionally calls __init__ with the same arguments as
        # __new__ once it is invoked. We save the correct arguments here,
        # so that __init__ can use them when invoked for the first time.
        _init_args_from_original_callable = args
        _init_kwargs_from_original_callable = kwargs
        return object.__new__(cls)

    return _MockConstructorDSL(
        target=mocked_class,
        method="__new__",
        cls=mocked_class,
        callable_mock=callable_mock,
        original_callable=original_callable,
    )
