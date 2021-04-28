# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import inspect
from typing import Any, Callable, Dict, Optional, Union


class _DescriptorProxy:
    def __init__(
        self,
        original_class_attr: Optional[Union[Callable, "_DescriptorProxy"]],
        attr_name: str,
    ) -> None:
        self.original_class_attr = original_class_attr
        self.attr_name = attr_name
        self.instance_attr_map: Dict[int, Callable] = {}

    def __set__(self, instance: object, value: Callable) -> None:
        self.instance_attr_map[id(instance)] = value

    def __get__(
        self, instance: object, owner: object
    ) -> Union[Callable, "_DescriptorProxy"]:
        if instance is None:
            return self
        if id(instance) in self.instance_attr_map:
            return self.instance_attr_map[id(instance)]
        else:
            if self.original_class_attr:
                return self.original_class_attr.__get__(instance, owner)  # type: ignore
            else:
                for parent in owner.mro()[1:]:  # type: ignore
                    method = parent.__dict__.get(self.attr_name, None)
                    if type(method) is type(self):
                        continue
                    if method:
                        return method.__get__(instance, owner)
                return instance.__get__(instance, owner)  # type: ignore

    def __delete__(self, instance: object) -> None:
        if instance in self.instance_attr_map:
            del self.instance_attr_map[id(instance)]


def _is_instance_method(target: Any, method: str) -> bool:
    if inspect.ismodule(target):
        return False

    if inspect.isclass(target):
        klass = target
    else:
        klass = type(target)

    for k in klass.mro():
        if method in k.__dict__:
            value = k.__dict__[method]
            if isinstance(value, _DescriptorProxy):
                value = value.original_class_attr
            if inspect.isfunction(value):
                return True
    return False


def _mock_instance_attribute(instance: Any, attr: str, value: Any) -> Callable:
    """
    Patch attribute at instance with given value. This works for any instance
    attribute, even when the attribute is defined via the descriptor protocol using
    __get__ at the class (eg with @property).

    This allows mocking of the attribute only at the desired instance, as opposed to
    using Python's unittest.mock.patch.object + PropertyMock, that requires patching
    at the class level, thus affecting all instances (not only the one you want).
    """
    klass = type(instance)
    class_restore_value = klass.__dict__.get(attr, None)
    setattr(klass, attr, _DescriptorProxy(class_restore_value, attr))
    setattr(instance, attr, value)

    def unpatch_class() -> None:
        if class_restore_value:
            setattr(klass, attr, class_restore_value)
        else:
            delattr(klass, attr)

    return unpatch_class


def _patch(
    target: Any, attribute: str, new_value: Any, restore: Any, restore_value: Any = None
) -> Callable:
    if _is_instance_method(target, attribute):
        unpatcher = _mock_instance_attribute(target, attribute, new_value)
    elif hasattr(type(target), attribute) and isinstance(
        getattr(type(target), attribute), property
    ):
        original_property = getattr(type(target), attribute)
        setattr(type(target), attribute, property(fget=lambda _: new_value))

        def unpatcher() -> None:
            if restore_value:
                setattr(type(target), attribute, original_property)
            else:
                delattr(target, attribute)

    else:
        setattr(target, attribute, new_value)

        def unpatcher() -> None:
            if restore_value:
                setattr(target, attribute, restore_value)

            else:
                delattr(target, attribute)

    return unpatcher
