# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import functools
from re import sub as _sub

from . import Context as _Context
from . import before_once_functions as _before_once_functions  # noqa: F401

from . import Skip  # noqa: F401


class _DSLContext(object):
    """
    This class implement TestSlide DSL. This is not intended to be used
    directly.
    """

    def __init__(self, current_context=None, skip=False, focus=False):
        self.current_context = current_context
        self.skip = skip
        self.focus = focus

    @staticmethod
    def _not_callable(*args, **kwargs):
        raise BaseException("This function should not be called outside test code.")

    @staticmethod
    def _name_from_function(func):
        return _sub("_", " ", func.__name__)

    def _create_context(self, name, context_code, *args, **kwargs):
        if not self.current_context:
            new_context = _Context(name, skip=self.skip, focus=self.focus)
        else:
            new_context = self.current_context.add_child_context(
                name, skip=self.skip, focus=self.focus
            )
        context_code(
            type(self)(current_context=new_context, skip=self.skip, focus=self.focus),
            *args,
            **kwargs
        )
        return self._not_callable

    def __call__(self, arg):
        if callable(arg):
            context_code = arg
            name = self._name_from_function(context_code)
            return self._create_context(name, context_code)
        else:
            name = arg
            return functools.partial(self._create_context, name)

    def _reset(self):
        self.skip = False
        self.focus = False

    def _require_context(action):  # noqa: B902
        def wrapper(func):
            @functools.wraps(func)
            def func_with_context_validation(self, *args, **kwargs):
                if not self.current_context:
                    raise TypeError(
                        "Can not {} without a parent context".format(action)
                    )
                return func(self, *args, **kwargs)

            return func_with_context_validation

        return wrapper

    # nested contexts

    def sub_context(self, arg):
        self._reset()
        return self(arg)

    def xsub_context(self, arg):
        self._reset()
        self.skip = True
        return self(arg)

    def fsub_context(self, arg):
        self._reset()
        self.focus = True
        return self(arg)

    # Examples

    @_require_context("create example")
    def _create_example(self, name, example_code, skip, focus):
        self.current_context.add_example(name, example_code, skip=skip, focus=focus)
        return self._not_callable

    def example(self, arg, skip=False, focus=False):
        if callable(arg):
            example_code = arg
            name = self._name_from_function(example_code)
            return self._create_example(name, example_code, skip=skip, focus=focus)
        else:
            name = arg
            return functools.partial(self._create_example, name, skip=skip, focus=focus)

    def xexample(self, arg):
        return self.example(arg, skip=True)

    def fexample(self, arg):
        return self.example(arg, focus=True)

    # Shared contexts

    @_require_context("create a shared context")
    def _create_shared_context(self, name, shared_context_code):
        self.current_context.add_shared_context(name, shared_context_code)
        return self._not_callable

    def shared_context(self, arg):
        if callable(arg):
            shared_context_code = arg
            name = self._name_from_function(shared_context_code)
            return self._create_shared_context(name, shared_context_code)
        else:
            name = arg
            return functools.partial(self._create_shared_context, name)

    @_require_context("merge a shared context")
    def merge_context(self, name, *args, **kwargs):
        if name not in self.current_context.all_shared_contexts:
            raise TypeError('Shared context "{}" does not exist'.format(name))
        self.current_context.all_shared_contexts[name](self, *args, **kwargs)

    @_require_context("merge a TestCase")
    def merge_test_case(self, test_case, attr_name):
        self.current_context.add_test_case(test_case, attr_name)
        return self._not_callable

    @_require_context("nest a shared context")
    def nest_context(self, name, *args, **kwargs):
        if name not in self.current_context.all_shared_contexts:
            raise TypeError('Shared context "{}" does not exist'.format(name))
        self._create_context(
            name, self.current_context.all_shared_contexts[name], *args, **kwargs
        )

    # Helper function

    @_require_context("create functions")
    def function(self, function_code):
        self.current_context.add_function(function_code.__name__, function_code)
        return self._not_callable

    # Memoizable attributes

    @_require_context("create memoizable attributes")
    def memoize(self, name_or_code=None, memoizable_code=None, **kwargs):
        if name_or_code:
            if kwargs:
                raise ValueError("Invalid arguments!")
            if memoizable_code:  # name + code
                name = name_or_code
            else:  # used as decorator
                name = name_or_code.__name__
                memoizable_code = name_or_code
            self.current_context.add_memoized_attribute(name, memoizable_code)
        else:  # kwargs
            if name_or_code or memoizable_code:
                raise ValueError("Invalid arguments!")
            for name, code in kwargs.items():
                self.memoize(name, code)
        return self._not_callable

    @_require_context("create a memoize before attribute")
    def memoize_before(self, name_or_code, memoizable_code=None):
        if memoizable_code:  # Got a lambda
            name = name_or_code
        else:  # Got a function
            name = name_or_code.__name__
            memoizable_code = name_or_code

        self.current_context.register_runtime_attribute(name)

        def materialize_attribute(self):
            setattr(self, name, memoizable_code(self))

        self.before(materialize_attribute)
        return self._not_callable

    # Hooks

    @_require_context("register before hook")
    def before(self, before_code):
        if not self.current_context:
            raise TypeError("Can not register before hook at top level context")
        self.current_context.before_functions.append(before_code)
        return self._not_callable

    @_require_context("register after hook")
    def after(self, after_code):
        self.current_context.after_functions.append(after_code)
        return self._not_callable

    @_require_context("register around hook")
    def around(self, around_code):
        if not self.current_context:
            raise TypeError("Can not register around hook at top level context")
        self.current_context.around_functions.append(around_code)
        return self._not_callable


context = _DSLContext()

xcontext = _DSLContext(skip=True)

fcontext = _DSLContext(focus=True)


def before_once(code):
    _before_once_functions.append(code)
