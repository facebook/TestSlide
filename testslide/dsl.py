# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import functools
import inspect
from functools import partial
from re import sub as _sub
from typing import Any, Callable, Optional, Union

from testslide import Context, TestCase

from . import Context as _Context
from . import Skip  # noqa: F401


def _validate_parameter(
    code: Callable, name: str, index: int, allow_async: bool = True
) -> None:
    parameters = list(inspect.signature(code).parameters.keys())
    if not parameters or parameters[index] != name:
        raise ValueError(
            f"Function must receive parameter #{index+1} named "
            f"'{name}', but given function has parameters: {parameters}."
        )
    if not allow_async and inspect.iscoroutinefunction(code):
        raise RuntimeError(
            f"TestSlide DSL context function `{code.__name__}` can not be async!"
        )


def _require_context(action: str) -> Callable:
    def wrapper(func: Callable) -> Callable:
        @functools.wraps(func)
        def func_with_context_validation(
            self: "_DSLContext", *args: Any, **kwargs: Any
        ) -> None:
            if not self.current_context:
                raise TypeError("Can not {} without a parent context".format(action))
            return func(self, *args, **kwargs)

        return func_with_context_validation

    return wrapper


class _DSLContext:
    """
    This class implement TestSlide DSL. This is not intended to be used
    directly.
    """

    def __init__(
        self,
        current_context: Optional[Context] = None,
        skip: bool = False,
        focus: bool = False,
    ) -> None:
        self.current_context = current_context
        self.skip = skip
        self.focus = focus

    @staticmethod
    def _not_callable(*args: Any, **kwargs: Any) -> None:
        raise BaseException("This function should not be called outside test code.")

    @staticmethod
    def _name_from_function(func: Callable) -> str:
        return _sub("_", " ", func.__name__)

    def _create_context(
        self, name: str, context_code: Callable, *args: Any, **kwargs: Any
    ) -> Callable:
        if not self.current_context:
            new_context = _Context(name, skip=self.skip, focus=self.focus)
        else:
            new_context = self.current_context.add_child_context(
                name, skip=self.skip, focus=self.focus
            )
        _validate_parameter(context_code, "context", 0, allow_async=False)
        context_code(
            type(self)(current_context=new_context, skip=self.skip, focus=self.focus),
            *args,
            **kwargs,
        )
        return self._not_callable

    def __call__(self, arg: Union[str, Callable]) -> Union[partial, Callable]:
        if callable(arg):
            context_code = arg
            name = self._name_from_function(context_code)
            return self._create_context(name, context_code)
        else:
            name = arg
            return functools.partial(self._create_context, name)

    def _reset(self) -> None:
        self.skip = False
        self.focus = False

    # nested contexts

    def sub_context(self, arg: Union[str, Callable]) -> Union[partial, Callable]:
        self._reset()
        return self(arg)

    def xsub_context(self, arg: Callable) -> Callable:
        self._reset()
        self.skip = True
        return self(arg)

    def fsub_context(self, arg: Callable) -> Callable:
        self._reset()
        self.focus = True
        return self(arg)

    # Examples

    @_require_context("create example")
    def _create_example(
        self, name: Optional[str], example_code: Callable, skip: bool, focus: bool
    ) -> Callable:
        if name is None:
            name = self._name_from_function(example_code)
        _validate_parameter(example_code, "self", 0)
        self.current_context.add_example(name, example_code, skip=skip, focus=focus)  # type: ignore
        return self._not_callable

    def example(
        self,
        arg: Optional[Union[str, Callable]] = None,
        skip: bool = False,
        focus: bool = False,
        skip_unless: bool = True,
    ) -> Union[partial, Callable]:
        skip = skip or not skip_unless
        if callable(arg):
            example_code = arg
            name = self._name_from_function(example_code)
            return self._create_example(name, example_code, skip=skip, focus=focus)
        else:
            name = arg  # type: ignore
            return functools.partial(self._create_example, name, skip=skip, focus=focus)

    def xexample(self, arg: Union[str, Callable]) -> Callable:
        return self.example(arg, skip=True)

    def fexample(self, arg: Union[str, Callable]) -> Callable:
        return self.example(arg, focus=True)

    # Shared contexts

    @_require_context("create a shared context")
    def _create_shared_context(
        self, name: str, shared_context_code: Callable
    ) -> Callable:
        _validate_parameter(shared_context_code, "context", 0)
        self.current_context.add_shared_context(name, shared_context_code)  # type: ignore
        return self._not_callable

    def shared_context(self, arg: Union[str, Callable]) -> Union[partial, Callable]:
        if callable(arg):
            shared_context_code = arg
            name = self._name_from_function(shared_context_code)
            return self._create_shared_context(name, shared_context_code)
        else:
            name = arg
            return functools.partial(self._create_shared_context, name)

    @_require_context("merge a shared context")
    def merge_context(self, name: str, *args: Any, **kwargs: Any) -> None:
        if name not in self.current_context.all_shared_contexts:  # type: ignore
            raise TypeError('Shared context "{}" does not exist'.format(name))
        self.current_context.all_shared_contexts[name](self, *args, **kwargs)  # type: ignore

    @_require_context("merge a TestCase")
    def merge_test_case(self, test_case: "TestCase", attr_name: str) -> Callable:
        self.current_context.add_test_case(test_case, attr_name)  # type:ignore
        return self._not_callable

    @_require_context("nest a shared context")
    def nest_context(self, name: str, *args: Any, **kwargs: Any) -> None:
        if name not in self.current_context.all_shared_contexts:  # type:ignore
            raise TypeError('Shared context "{}" does not exist'.format(name))
        self._create_context(
            name, self.current_context.all_shared_contexts[name], *args, **kwargs  # type: ignore
        )

    # Helper function

    @_require_context("create functions")
    def function(self, function_code: Callable) -> Callable:
        _validate_parameter(function_code, "self", 0)
        self.current_context.add_function(function_code.__name__, function_code)  # type: ignore
        return self._not_callable

    # Memoizable attributes

    @_require_context("create memoizable attributes")
    def memoize(
        self,
        name_or_code: Optional[Union[str, Callable]] = None,
        memoizable_code: Optional[Callable] = None,
        **kwargs: Any,
    ) -> Callable:
        _memoizable_code: Callable
        if name_or_code:
            if kwargs:
                raise ValueError("Invalid arguments!")
            if memoizable_code:  # name + code
                name = name_or_code
                _memoizable_code = memoizable_code
            else:  # used as decorator
                name = name_or_code.__name__  # type: ignore
                _memoizable_code = name_or_code  # type: ignore
            _validate_parameter(_memoizable_code, "self", 0)
            self.current_context.add_memoized_attribute(name, _memoizable_code)  # type: ignore
        else:  # kwargs
            if name_or_code or memoizable_code:
                raise ValueError("Invalid arguments!")
            for name, code in kwargs.items():
                self.memoize(name, code)
        return self._not_callable

    @_require_context("create a memoize before attribute")
    def memoize_before(
        self,
        name_or_code: Union[str, Callable],
        memoizable_code: Optional[Callable] = None,
    ) -> Callable:
        _memoizable_code: Callable
        if memoizable_code:  # Got a lambda
            name = name_or_code
            _memoizable_code = memoizable_code
        else:  # Got a function
            name = name_or_code.__name__  # type: ignore
            _memoizable_code = name_or_code  # type: ignore

        _validate_parameter(_memoizable_code, "self", 0)

        self.current_context.add_memoized_attribute(name, _memoizable_code, before=True)  # type: ignore

        return self._not_callable

    # Hooks

    @_require_context("register before hook")
    def before(self, before_code: Callable) -> Callable:
        _validate_parameter(before_code, "self", 0)
        if not self.current_context:
            raise TypeError("Can not register before hook at top level context")
        self.current_context.before_functions.append(before_code)
        return self._not_callable

    @_require_context("register after hook")
    def after(self, after_code: Callable) -> Callable:
        _validate_parameter(after_code, "self", 0)
        self.current_context.after_functions.append(after_code)  # type: ignore
        return self._not_callable

    @_require_context("register around hook")
    def around(self, around_code: Callable) -> Callable:
        _validate_parameter(around_code, "self", 0)
        _validate_parameter(around_code, "wrapped", 1)
        if not self.current_context:
            raise TypeError("Can not register around hook at top level context")
        self.current_context.around_functions.append(around_code)
        return self._not_callable


context = _DSLContext()

xcontext = _DSLContext(skip=True)

fcontext = _DSLContext(focus=True)
