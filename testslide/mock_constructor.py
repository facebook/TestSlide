# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import gc
import inspect
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, Union

import testslide
from testslide.mock_callable import _CallableMock, _MockCallableDSL

from .lib import (
    _bail_if_private,
    _validate_callable_arg_types,
    _validate_callable_signature,
)

_DO_NOT_COPY_CLASS_ATTRIBUTES = (
    "__dict__",
    "__doc__",
    "__module__",
    "__new__",
    "__slots__",
)


_unpatchers: List[Callable] = []
_mocked_target_classes: Dict[Union[int, Tuple[int, str]], Tuple[type, object]] = {}
_restore_dict: Dict[Union[int, Tuple[int, str]], Dict[str, Any]] = {}
_init_args_from_original_callable: Optional[Tuple[Any, ...]] = None
_init_kwargs_from_original_callable: Optional[Dict[str, Any]] = None
_mocked_class_by_original_class_id: Dict[Union[Tuple[int, str], int], type] = {}
_target_class_id_by_original_class_id: Dict[int, Union[Tuple[int, str], int]] = {}


def _get_class_or_mock(original_class: Any) -> Any:
    """
    If given class was not a target for mock_constructor, return it.
    Otherwise, return the mocked subclass.
    """
    return _mocked_class_by_original_class_id.get(id(original_class), original_class)


def _is_mocked_class(klass: Type[object]) -> bool:
    return id(klass) in [id(k) for k in _mocked_class_by_original_class_id.values()]


def unpatch_all_constructor_mocks() -> None:
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

    _NAME: str = "mock_constructor"

    def __init__(
        self,
        target: Union[type, str, object],
        method: str,
        cls: object,
        callable_mock: Union[
            Optional[Callable[[Type[object]], Any]], Optional[_CallableMock]
        ] = None,
        original_callable: Optional[Callable] = None,
    ) -> None:
        self.cls = cls
        caller_frame = inspect.currentframe().f_back  # type: ignore
        # loading the context ends up reading files from disk and that might block
        # the event loop, so we don't do it.
        caller_frame_info = inspect.getframeinfo(caller_frame, context=0)  # type: ignore
        super(_MockConstructorDSL, self).__init__(  # type: ignore
            target,
            method,
            caller_frame_info,
            callable_mock=callable_mock,
            original_callable=original_callable,
        )

    def for_call(self, *args: Any, **kwargs: Any) -> "_MockConstructorDSL":
        return super(_MockConstructorDSL, self).for_call(  # type: ignore
            *((self.cls,) + args), **kwargs
        )

    def with_wrapper(self, func: Callable) -> "_MockConstructorDSL":
        def new_func(
            original_callable: Callable, cls: object, *args: Any, **kwargs: Any
        ) -> Any:
            assert cls == self.cls

            def new_original_callable(*args: Any, **kwargs: Any) -> Any:
                return original_callable(cls, *args, **kwargs)

            return func(new_original_callable, *args, **kwargs)

        return super(_MockConstructorDSL, self).with_wrapper(new_func)  # type: ignore

    def with_implementation(self, func: Callable) -> "_MockConstructorDSL":
        def new_func(cls: object, *args: Any, **kwargs: Any) -> Any:
            assert cls == self.cls
            return func(*args, **kwargs)

        return super(_MockConstructorDSL, self).with_implementation(new_func)  # type: ignore


def _get_original_init(original_class: type, instance: object, owner: type) -> Any:
    target_class_id = _target_class_id_by_original_class_id[id(original_class)]
    # If __init__ available at the class __dict__...
    if "__init__" in _restore_dict[target_class_id]:
        # Use it,
        return _restore_dict[target_class_id]["__init__"].__get__(instance, owner)
    else:
        # otherwise, pull from a parent class.
        return original_class.__init__.__get__(instance, owner)  # type: ignore


class AttrAccessValidation:
    EXCEPTION_MESSAGE = (
        "Attribute {} after the class has been used with mock_constructor() "
        "is not supported! After using mock_constructor() you must get a "
        "pointer to the new mocked class (eg: {}.{})."
    )

    def __init__(self, name: str, original_class: type, mocked_class: type) -> None:
        self.name = name
        self.original_class = original_class
        self.mocked_class = mocked_class

    def __get__(
        self, instance: Optional[type], owner: Type[type]
    ) -> Union[Callable, str]:
        mro = owner.mro()  # type: ignore
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

    def __set__(self, instance: object, value: Any) -> None:
        raise BaseException(
            self.EXCEPTION_MESSAGE.format(
                "setting", self.original_class.__module__, self.original_class.__name__
            )
        )

    def __delete__(self, instance: object) -> None:
        raise BaseException(
            self.EXCEPTION_MESSAGE.format(
                "deleting", self.original_class.__module__, self.original_class.__name__
            )
        )


def _wrap_type_validation(
    template: object, callable_mock: _CallableMock, callable_templates: List[Callable]
) -> Callable:
    def callable_mock_with_type_validation(*args: Any, **kwargs: Any) -> Any:
        for callable_template in callable_templates:
            if _validate_callable_signature(
                False,
                callable_template,
                template,
                callable_template.__name__,
                args,
                kwargs,
            ):
                _validate_callable_arg_types(False, callable_template, args, kwargs)
        return callable_mock(*args, **kwargs)

    return callable_mock_with_type_validation


def _get_mocked_class(
    original_class: type,
    target_class_id: Union[Tuple[int, str], int],
    callable_mock: _CallableMock,
    type_validation: bool,
) -> type:
    if target_class_id in _target_class_id_by_original_class_id:
        raise RuntimeError("Can not mock the same class at two different modules!")
    else:
        _target_class_id_by_original_class_id[id(original_class)] = target_class_id

    original_class_new = original_class.__new__
    original_class_init = original_class.__init__  # type: ignore

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
    mocked_class_dict = {
        "__new__": _wrap_type_validation(
            original_class,
            callable_mock,
            [
                original_class_new,
                original_class_init,
            ],
        )
        if type_validation
        else callable_mock
    }
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
    def init_with_correct_args(self: object, *args: Any, **kwargs: Any) -> None:
        global _init_args_from_original_callable, _init_kwargs_from_original_callable
        if None not in [
            _init_args_from_original_callable,
            _init_kwargs_from_original_callable,
        ]:
            args = _init_args_from_original_callable  # type: ignore
            kwargs = _init_kwargs_from_original_callable  # type: ignore

        original_init = _get_original_init(
            original_class, instance=self, owner=mocked_class
        )
        try:
            original_init(*args, **kwargs)
        finally:
            _init_args_from_original_callable = None
            _init_kwargs_from_original_callable = None

    mocked_class.__init__ = init_with_correct_args  # type: ignore

    return mocked_class


def _patch_and_return_mocked_class(
    target: object,
    class_name: str,
    target_class_id: Union[Tuple[int, str], int],
    original_class: type,
    callable_mock: _CallableMock,
    type_validation: bool,
) -> type:
    mocked_class = _get_mocked_class(
        original_class, target_class_id, callable_mock, type_validation
    )

    def unpatcher() -> None:
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


def mock_constructor(
    target: str,
    class_name: str,
    allow_private: bool = False,
    type_validation: bool = True,
) -> _MockConstructorDSL:
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

        caller_frame = inspect.currentframe().f_back  # type: ignore
        # loading the context ends up reading files from disk and that might block
        # the event loop, so we don't do it.
        caller_frame_info = inspect.getframeinfo(caller_frame, context=0)  # type: ignore
        callable_mock = _CallableMock(original_class, "__new__", caller_frame_info)
        mocked_class = _patch_and_return_mocked_class(
            target,
            class_name,
            target_class_id,
            original_class,
            callable_mock,
            type_validation,
        )

    def original_callable(cls: type, *args: Any, **kwargs: Any) -> Any:
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
