# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import six
import inspect
import types
import functools
from typing import List, Callable  # noqa
import testslide
from testslide.strict_mock import StrictMock
from testslide.strict_mock import _add_signature_validation


def mock_callable(target, method):
    if method == "__new__":
        raise ValueError(
            "Mocking __new__ is not allowed with mock_callable(), please use "
            "mock_constructor()."
        )
    return _MockCallableDSL(target, method)


_unpatchers = []  # type: List[Callable]  # noqa T484


def unpatch_all_callable_mocks():
    """
    This method must be called after every test unconditionally to remove all
    active mock_callable() patches.
    """
    try:
        for unpatcher in _unpatchers:
            unpatcher()
    finally:
        del _unpatchers[:]


def register_assertion(assertion):
    """
    This method must be redefined by the test framework using mock_callable().
    It will be called when a new assertion is defined, passing a callable as an
    argument that evaluates that assertion. Every defined assertion during a test
    must be called after the test code ends, and before the test finishes.
    """
    raise NotImplementedError("This method must be redefined by the test framework")


def _format_target(target):
    if hasattr(target, "__repr__"):
        return repr(target)
    else:
        return "{}.{} instance with id {}".format(
            target.__module__, type(target).__name__, id(target)
        )


def _format_args(indent, *args, **kwargs):
    indentation = "  " * indent
    s = ("{}{}\n" "{}").format(indentation, args, indentation)
    s += "{"
    if kwargs:
        s += "\n"
        for k, v in kwargs.items():
            s += "{}  {}={},\n".format(indentation, k, v)
        s += "{}".format(indentation)
    s += "}\n"
    return s


class UndefinedBehaviorForCall(BaseException):
    """
    Raised when a mock receives a call for which no behavior was defined.

    Inherits from BaseException to avoid being caught by tested code.
    """


class UnexpectedCallReceived(BaseException):
    """
    Raised when a mock receives a call that it is configured not to accept.

    Inherits from BaseException to avoid being caught by tested code.
    """


class UnexpectedCallArguments(BaseException):
    """
    Raised when a mock receives a call with unexpected arguments.

    Inherits from BaseException to avoid being caught by tested code.
    """


##
## Behavior
##


class _Runner(object):
    def __init__(self, target, method, original_callable):
        self.target = target
        self.method = method
        self.original_callable = original_callable
        self.accepted_args = None
        self.call_count = 0

    def run(self, *args, **kwargs):
        self.call_count += 1

    def add_accepted_args(self, *args, **kwargs):
        # TODO validate if args match callable signature
        self.accepted_args = (args, kwargs)

    def can_accept_args(self, *args, **kwargs):
        if self.accepted_args:
            if self.accepted_args == (args, kwargs):
                return True
            return False
        else:
            return True

    def _args_message(self):
        if self.accepted_args:
            return "arguments:\n{}".format(
                _format_args(2, *self.accepted_args[0], **self.accepted_args[1])
            )
        else:
            return "any arguments "

    def add_exact_calls_assertion(self, times):
        def assertion():
            if times != self.call_count:
                raise AssertionError(
                    (
                        "calls did not match assertion.\n"
                        "{}, {}:\n"
                        "  expected: called exactly {} time(s) with {}"
                        "  received: {} call(s)"
                    ).format(
                        _format_target(self.target),
                        repr(self.method),
                        times,
                        self._args_message(),
                        self.call_count,
                    )
                )

        register_assertion(assertion)

    def add_at_least_calls_assertion(self, times):
        def assertion():
            if self.call_count < times:
                raise AssertionError(
                    (
                        "calls did not match assertion.\n"
                        "{}, {}:\n"
                        "  expected: called at least {} time(s) with {}"
                        "  received: {} call(s)"
                    ).format(
                        _format_target(self.target),
                        repr(self.method),
                        times,
                        self._args_message(),
                        self.call_count,
                    )
                )

        register_assertion(assertion)

    def add_at_most_calls_assertion(self, times):
        def assertion():
            if not self.call_count or self.call_count > times:
                raise AssertionError(
                    (
                        "calls did not match assertion.\n"
                        "{}, {}:\n"
                        "  expected: called at most {} time(s) with {}"
                        "  received: {} call(s)"
                    ).format(
                        _format_target(self.target),
                        repr(self.method),
                        times,
                        self._args_message(),
                        self.call_count,
                    )
                )

        register_assertion(assertion)


class _ReturnValueRunner(_Runner):
    def __init__(self, target, method, original_callable, value):
        super(_ReturnValueRunner, self).__init__(target, method, original_callable)
        self.return_value = value

    def run(self, *args, **kwargs):
        super(_ReturnValueRunner, self).run(*args, **kwargs)
        return self.return_value


class _ReturnValuesRunner(_Runner):
    def __init__(self, target, method, original_callable, values_list):
        super(_ReturnValuesRunner, self).__init__(target, method, original_callable)
        # Reverse original list for popping efficiency
        self.values_list = list(reversed(values_list))

    def run(self, *args, **kwargs):
        super(_ReturnValuesRunner, self).run(*args, **kwargs)
        if self.values_list:
            return self.values_list.pop()
        else:
            raise UndefinedBehaviorForCall("No more values to return!")


class _YieldValuesRunner(_Runner):
    def __init__(self, target, method, original_callable, values_list):
        super(_YieldValuesRunner, self).__init__(target, method, original_callable)
        self.values_list = values_list
        self.index = 0

    def __iter__(self):
        return self

    def __next__(self):
        try:
            item = self.values_list[self.index]
        except IndexError:
            raise StopIteration()
        self.index += 1
        return item

    if six.PY2:
        next = __next__

    def run(self, *args, **kwargs):
        super(_YieldValuesRunner, self).run(*args, **kwargs)
        return self


class _RaiseRunner(_Runner):
    def __init__(self, target, method, original_callable, exception):
        super(_RaiseRunner, self).__init__(target, method, original_callable)
        self.exception = exception

    def run(self, *args, **kwargs):
        super(_RaiseRunner, self).run(*args, **kwargs)
        raise self.exception


class _ImplementationRunner(_Runner):
    def __init__(self, target, method, original_callable, new_implementation):
        super(_ImplementationRunner, self).__init__(target, method, original_callable)
        self.new_implementation = new_implementation

    def run(self, *args, **kwargs):
        super(_ImplementationRunner, self).run(*args, **kwargs)
        return self.new_implementation(*args, **kwargs)


class _CallOriginalRunner(_Runner):
    def run(self, *args, **kwargs):
        super(_CallOriginalRunner, self).run(*args, **kwargs)
        return self.original_callable(*args, **kwargs)


class _CallableMock(object):
    def __init__(self, target, method):
        self.target = target
        self.method = method
        self.runners = []

    def __call__(self, *args, **kwargs):
        for runner in self.runners:
            if runner.can_accept_args(*args, **kwargs):
                return runner.run(*args, **kwargs)
        ex_msg = (
            "{}, {}:\n"
            "  Received call:\n"
            "{}"
            "  But no behavior was defined for it."
        ).format(
            _format_target(self.target),
            repr(self.method),
            _format_args(2, *args, **kwargs),
        )
        if self._registered_calls:
            ex_msg += "\n  These are the registered calls:\n" "{}".format(
                "".join(
                    _format_args(2, *reg_args, **reg_kwargs)
                    for reg_args, reg_kwargs in self._registered_calls
                )
            )
            raise UnexpectedCallArguments(ex_msg)
        raise UndefinedBehaviorForCall(ex_msg)

    @property
    def _registered_calls(self):
        return [runner.accepted_args for runner in self.runners if runner.accepted_args]


class _DescriptorProxy(object):
    def __init__(self, original_class_attr, attr_name):
        self.original_class_attr = original_class_attr
        self.attr_name = attr_name
        self.instance_attr_map = {}

    def __set__(self, instance, value):
        self.instance_attr_map[id(instance)] = value

    def __get__(self, instance, owner):
        if instance is None:
            return self
        if id(instance) in self.instance_attr_map:
            return self.instance_attr_map[id(instance)]
        else:
            if self.original_class_attr:
                return self.original_class_attr.__get__(instance, owner)
            else:
                for parent in owner.mro()[1:]:
                    method = parent.__dict__.get(self.attr_name, None)
                    if type(method) is type(self):
                        continue
                    if method:
                        return method.__get__(instance, owner)
                return instance.__get__(instance, owner)

    def __delete__(self, instance):
        if instance in self.instance_attr_map:
            del self.instance_attr_map[instance]


def _is_instance_method(target, method):
    if inspect.ismodule(target):
        return False

    if inspect.isclass(target):
        klass = target
    else:
        klass = type(target)

    for k in klass.mro():
        if method in k.__dict__ and inspect.isfunction(k.__dict__[method]):
            return True
    return False


def _mock_instance_attribute(instance, attr, value):
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

    def unpatch_class():
        if class_restore_value:
            setattr(klass, attr, class_restore_value)
        else:
            delattr(klass, attr)

    return unpatch_class


def _patch(target, method, new_value):
    if isinstance(target, six.string_types):
        target = testslide._importer(target)

    if isinstance(target, StrictMock):
        original_callable = None
    else:
        original_callable = getattr(target, method)

    new_value = _add_signature_validation(new_value, target, method)
    restore_value = target.__dict__.get(method, None)

    if inspect.isclass(target):
        if _is_instance_method(target, method):
            raise ValueError(
                "Patching an instance method at the class is not supported: "
                "bugs are easy to introduce, as patch is not scoped for an "
                "instance, which can potentially even break class behavior; "
                "assertions on calls are ambiguous (for every instance or one "
                "global assertion?)."
            )
        new_value = staticmethod(new_value)

    if _is_instance_method(target, method):
        unpatcher = _mock_instance_attribute(target, method, new_value)
    else:
        setattr(target, method, new_value)

        def unpatcher():
            if restore_value:
                setattr(target, method, restore_value)
            else:
                delattr(target, method)

    return original_callable, unpatcher


class _MockCallableDSL(object):

    CALLABLE_MOCKS = {}  # NOQA T484

    def __init__(
        self,
        target,
        method,
        callable_mock=None,
        original_callable=None,
        prepend_first_arg=None,
    ):
        self._original_target = target
        self._method = method
        self._runner = None
        self._next_runner_accepted_args = None
        self.prepend_first_arg = prepend_first_arg

        if isinstance(target, six.string_types):
            self._target = testslide._importer(target)
        else:
            self._target = target

        target_method_id = (id(target), method)

        if target_method_id not in self.CALLABLE_MOCKS:
            if not callable_mock:
                patch = True
                callable_mock = _CallableMock(self._original_target, self._method)
            else:
                patch = False
            self.CALLABLE_MOCKS[target_method_id] = callable_mock
            self._callable_mock = callable_mock

            def del_callable_mock():
                del self.CALLABLE_MOCKS[target_method_id]

            _unpatchers.append(del_callable_mock)

            if patch:
                original_callable, unpatcher = _patch(target, method, callable_mock)
                _unpatchers.append(unpatcher)
            self._original_callable = original_callable
            callable_mock.original_callable = original_callable
        else:
            self._callable_mock = self.CALLABLE_MOCKS[target_method_id]
            self._original_callable = self._callable_mock.original_callable

    def _add_runner(self, runner):
        if self._runner:
            raise ValueError(
                "Can't define more than one behavior using the same "
                "self.mock_callable() chain. Please call self.mock_callable() again "
                "one time for each new behavior."
            )
        if self._next_runner_accepted_args:
            args, kwargs = self._next_runner_accepted_args
            self._next_runner_accepted_args = None
            runner.add_accepted_args(*args, **kwargs)
        self._runner = runner
        self._callable_mock.runners.insert(0, runner)

    def _assert_runner(self):
        if not self._runner:
            raise ValueError(
                "You must first define a behavior. Eg: "
                "self.mock_callable(target, 'func')"
                ".to_return_value(value)"
                ".and_assert_called_exactly(times)"
            )

    ##
    ## Arguments
    ##

    def for_call(self, *args, **kwargs):
        """
        Filter for only calls like this.
        """
        if self.prepend_first_arg:
            args = (self.prepend_first_arg,) + args
        if self._runner:
            self._runner.add_accepted_args(*args, **kwargs)
        else:
            self._next_runner_accepted_args = (args, kwargs)
        return self

    ##
    ## Behavior
    ##

    def to_return_value(self, value):
        """
        Always return given value.
        """
        self._add_runner(
            _ReturnValueRunner(
                self._original_target, self._method, self._original_callable, value
            )
        )
        return self

    def to_return_values(self, values_list):
        """
        For each call, return each value from given list in order.
        When list is exhausted, goes to the next behavior set.
        """
        if not isinstance(values_list, list):
            raise ValueError("{} is not a list".format(values_list))
        self._add_runner(
            _ReturnValuesRunner(
                self._original_target,
                self._method,
                self._original_callable,
                values_list,
            )
        )
        return self

    def to_yield_values(self, values_list):
        """
        Callable will return an iterator what will yield each value from the
        given list.
        """
        if not isinstance(values_list, list):
            raise ValueError("{} is not a list".format(values_list))
        self._add_runner(
            _YieldValuesRunner(
                self._original_target,
                self._method,
                self._original_callable,
                values_list,
            )
        )
        return self

    def to_raise(self, ex):
        """
        Raises given exception class or exception instance.
        """
        if isinstance(ex, BaseException):
            self._add_runner(
                _RaiseRunner(
                    self._original_target, self._method, self._original_callable, ex
                )
            )
        elif isinstance(ex(), BaseException):
            self._add_runner(
                _RaiseRunner(
                    self._original_target, self._method, self._original_callable, ex()
                )
            )
        else:
            raise ValueError(
                "{} is not subclass or instance of BaseException".format(ex)
            )
        return self

    def with_implementation(self, func):
        """
        Replace callable by given function.
        """
        if not callable(func):
            raise ValueError("{} must be callable.".format(func))
        self._add_runner(
            _ImplementationRunner(
                self._original_target, self._method, self._original_callable, func
            )
        )
        return self

    def with_wrapper(self, func):
        """
        Replace callable with given wrapper function, that will be called as:

          func(original_func, *args, **kwargs)

        receiving the original function as the first argument as well as any given
        arguments.
        """
        if not callable(func):
            raise ValueError("{} must be callable.".format(func))

        if not self._original_callable:
            raise ValueError("Can not wrap original callable that does not exist.")

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if self.prepend_first_arg and args:
                assert (
                    args[0] == self.prepend_first_arg
                ), "Received unexpected first argument: {}.".format(args[0])
                args = args[1:]
            return func(self._original_callable, *args, **kwargs)

        self._add_runner(
            _ImplementationRunner(
                self._original_target, self._method, self._original_callable, wrapper
            )
        )
        return self

    def to_call_original(self):
        """
        Calls the original callable implementation, instead of mocking it. This is
        useful for example, if you want to by default call the original implementation,
        but for a specific calls, mock the result.
        """
        if not self._original_callable:
            raise ValueError("Can not call original callable that does not exist.")
        self._add_runner(
            _CallOriginalRunner(
                self._original_target, self._method, self._original_callable
            )
        )
        return self

    ##
    ## Call Assertions
    ##

    def and_assert_called_exactly(self, count):
        """
        Assert that there were exactly the given number of calls.
        """
        self._assert_runner()
        self._runner.add_exact_calls_assertion(count)
        return self

    def and_assert_called_once(self):
        """
        Short for and_assert_called_exactly(1)
        """
        return self.and_assert_called_exactly(1)

    def and_assert_called_twice(self):
        """
        Short for and_assert_called_exactly(2)
        """
        return self.and_assert_called_exactly(2)

    def and_assert_called_at_least(self, count):
        """
        Assert that there at least the given number of calls.
        """
        if count < 1:
            raise ValueError("times must be >= 1")
        self._assert_runner()
        self._runner.add_at_least_calls_assertion(count)
        return self

    def and_assert_called_at_most(self, count):
        """
        Assert that there at most the given number of calls.
        """
        if count < 1:
            raise ValueError("times must be >= 1")
        self._assert_runner()
        self._runner.add_at_most_calls_assertion(count)
        return self

    def and_assert_called(self):
        """
        Short for self.and_assert_called_at_least(1).
        """
        return self.and_assert_called_at_least(1)

    def and_assert_not_called(self):
        """
        Disallow calls, by raising UnexpectedCallReceived.
        """
        self._assert_runner()
        self._runner.add_exact_calls_assertion(0)
        return self
