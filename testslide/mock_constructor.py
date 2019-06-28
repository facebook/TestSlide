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
from testslide.mock_callable import _MockCallableDSL, _CallableMock, _Runner

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


def is_cls_mock(cls):
    return getattr(cls, "__mock", False) == True


class _ConstructorRunner(_Runner):
    def __init__(self, parent_runner):
        super(_ConstructorRunner, self).__init__(
            target=parent_runner.target,
            method="__new__",
            original_callable=parent_runner.original_callable,
        )

        self.parent = parent_runner

    @property
    def call_count(self):
        return self.parent.call_count

    def _set_max_calls(self, times):
        self.parent._set_max_calls(times)

    def add_accepted_args(self, *args, **kwargs):
        return self.parent.add_accepted_args(*args, **kwargs)

    def can_accept_args(self, *args, **kwargs):
        if not args or not is_cls_mock(args[0]):
            return False

        return self.parent.can_accept_args(*args[1:], **kwargs)

    def run(self, target_cls, *args, **kwargs):
        assert is_cls_mock(
            target_cls
        ), "ConstructorRunner called for non-mock class: {}".format(target_cls)

        return self.parent.run(*args, **kwargs)


class _MockConstructorDSL(_MockCallableDSL):
    """Specialized version of _MockCallableDSL to call __new__ with correct args"""

    def _add_runner(self, runner):
        wrapped_runner = _ConstructorRunner(runner)
        return super(_MockConstructorDSL, self)._add_runner(wrapped_runner)


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

        mocked_class = type(
            str(original_class.__name__ + "Mock"),
            (original_class,),
            {"__new__": callable_mock, "__mock": True},
        )
        mocked_class.__mock = True

        setattr(target, class_name, mocked_class)
        _mocked_classes[mocked_class_id] = (original_class, mocked_class)

    return _MockConstructorDSL(
        mocked_class,
        "__new__",
        callable_mock=callable_mock,
        original_callable=original_class,
    )
