# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import gc
import inspect

import testslide
from testslide.mock_callable import _MockCallableDSL, _CallableMock
from .lib import _bail_if_private

_DO_NOT_COPY_CLASS_ATTRIBUTES = (
    "__dict__",
    "__doc__",
    "__module__",
    "__new__",
    "__slots__",
)


_unpatchers = []
_mocked_target_classes = {}
_restore_dict = {}
_init_args_from_original_callable = None
_init_kwargs_from_original_callable = None
_mocked_class_by_original_class_id = {}
_target_class_id_by_original_class_id = {}


def _get_class_or_mock(original_class):
    """
    If given class was not a target for mock_constructor, return it.
    Otherwise, return the mocked subclass.
    """
    return _mocked_class_by_original_class_id.get(id(original_class), original_class)


def _is_mocked_class(klass):
    return id(klass) in [id(k) for k in _mocked_class_by_original_class_id.values()]


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

    def with_implementation(self, func):
        def new_func(cls, *args, **kwargs):
            assert cls == self.cls
            return func(*args, **kwargs)

        return super(_MockConstructorDSL, self).with_implementation(new_func)


def _get_original_init(original_class, instance, owner):
    target_class_id = _target_class_id_by_original_class_id[id(original_class)]
    # If __init__ available at the class __dict__...
    if "__init__" in _restore_dict[target_class_id]:
        # Use it,
        return _restore_dict[target_class_id]["__init__"].__get__(instance, owner)
    else:
        # otherwise, pull from a parent class.
        return original_class.__init__.__get__(instance, owner)


class AttrAccessValidation(object):
    EXCEPTION_MESSAGE = (
        "Attribute {} after the class has been used with mock_constructor() "
        "is not supported! After using mock_constructor() you must get a "
        "pointer to the new mocked class (eg: {}.{})."
    )

    def __init__(self, name, original_class, mocked_class):
        self.name = name
        self.original_class = original_class
        self.mocked_class = mocked_class

    def __get__(self, instance, owner):
        mro = owner.mro()
        # If owner is a subclass, allow it
        if mro.index(owner) < mro.index(self.original_class):
            parent_class = mro[mro.index(self.original_class) + 1]
            # and return the parent's value
            attr = getattr(parent_class, self.name)
            if hasattr(attr, "__get__"):
                return attr.__get__(instance, parent_class)
            else:
                return attr
        # For class level attributes & methods, we can make it work...
        elif instance is None and owner is self.original_class:
            # ...by returning the original value from the mocked class
            attr = getattr(self.mocked_class, self.name)
            if hasattr(attr, "__get__"):
                return attr.__get__(instance, self.mocked_class)
            else:
                return attr
        # Disallow for others
        else:
            raise BaseException(
                self.EXCEPTION_MESSAGE.format(
                    "getting",
                    self.original_class.__module__,
                    self.original_class.__name__,
                )
            )

    def __set__(self, instance, value):
        raise BaseException(
            self.EXCEPTION_MESSAGE.format(
                "setting", self.original_class.__module__, self.original_class.__name__
            )
        )

    def __delete__(self, instance):
        raise BaseException(
            self.EXCEPTION_MESSAGE.format(
                "deleting", self.original_class.__module__, self.original_class.__name__
            )
        )


def _get_mocked_class(original_class, target_class_id, callable_mock):
    if target_class_id in _target_class_id_by_original_class_id:
        raise RuntimeError("Can not mock the same class at two different modules!")
    else:
        _target_class_id_by_original_class_id[id(original_class)] = target_class_id
    # Extract class attributes from the target class...
    _restore_dict[target_class_id] = {}
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
            continue
        _restore_dict[target_class_id][name] = value
    # ...and reuse them...
    mocked_class_dict = {"__new__": callable_mock}
    mocked_class_dict.update(
        {
            name: value
            for name, value in _restore_dict[target_class_id].items()
            if name not in ("__new__", "__init__")
        }
    )

    # ...to create the mocked subclass...
    mocked_class = type(
        str(original_class.__name__), (original_class,), mocked_class_dict
    )

    # ...and deal with forbidden access to the original class
    for name in _restore_dict[target_class_id].keys():
        setattr(
            original_class,
            name,
            AttrAccessValidation(name, original_class, mocked_class),
        )

    # Because __init__ is called after __new__ unconditionally with the same
    # arguments, we need to mock it fir this first call, to call the real
    # __init__ with the correct arguments.
    def init_with_correct_args(self, *args, **kwargs):
        global _init_args_from_original_callable, _init_kwargs_from_original_callable
        if None not in [
            _init_args_from_original_callable,
            _init_kwargs_from_original_callable,
        ]:
            args = _init_args_from_original_callable
            kwargs = _init_kwargs_from_original_callable

        original_init = _get_original_init(
            original_class, instance=self, owner=mocked_class
        )
        try:
            original_init(*args, **kwargs)
        finally:
            _init_args_from_original_callable = None
            _init_kwargs_from_original_callable = None

    mocked_class.__init__ = init_with_correct_args

    return mocked_class


def _patch_and_return_mocked_class(
    target, class_name, target_class_id, original_class, callable_mock
):
    mocked_class = _get_mocked_class(original_class, target_class_id, callable_mock)

    def unpatcher():
        for name, value in _restore_dict[target_class_id].items():
            setattr(original_class, name, value)
        del _restore_dict[target_class_id]
        setattr(target, class_name, original_class)
        del _mocked_target_classes[target_class_id]
        del _mocked_class_by_original_class_id[id(original_class)]
        del _target_class_id_by_original_class_id[id(original_class)]

    _unpatchers.append(unpatcher)

    setattr(target, class_name, mocked_class)
    _mocked_target_classes[target_class_id] = (original_class, mocked_class)
    _mocked_class_by_original_class_id[id(original_class)] = mocked_class

    return mocked_class


def mock_constructor(target, class_name, allow_private=False):
    if not isinstance(class_name, str):
        raise ValueError("Second argument must be a string with the name of the class.")
    _bail_if_private(class_name, allow_private)
    if isinstance(target, str):
        target = testslide._importer(target)
    target_class_id = (id(target), class_name)

    if target_class_id in _mocked_target_classes:
        original_class, mocked_class = _mocked_target_classes[target_class_id]
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

        gc.collect()
        instances = [
            obj
            for obj in gc.get_referrers(original_class)
            if type(obj) is original_class
        ]
        if instances:
            raise RuntimeError(
                "mock_constructor() can not be used after instances of {} were created: {}".format(
                    class_name, instances
                )
            )

        if not inspect.isclass(original_class):
            raise ValueError("Target must be a class.")
        elif not issubclass(original_class, object):
            raise ValueError("Old style classes are not supported.")
        callable_mock = _CallableMock(original_class, "__new__")
        mocked_class = _patch_and_return_mocked_class(
            target, class_name, target_class_id, original_class, callable_mock
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
