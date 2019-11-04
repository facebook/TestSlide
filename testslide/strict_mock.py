# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import dis
import copy
import functools
import inspect
import os.path

from unittest.mock import _must_skip


def _add_signature_validation(value, template, attr_name):
    if isinstance(template, StrictMock):
        if "__template" in template.__dict__:
            template = template.__template
        else:
            return value

    # This covers runtime attributes
    if not hasattr(template, attr_name):
        return value

    callable_template = getattr(template, attr_name)
    # FIXME decouple from _must_skip. It tells when self should be skipped
    # for signature validation.
    if _must_skip(template, attr_name, isinstance(template, type)):
        callable_template = functools.partial(callable_template, None)

    try:
        signature = inspect.signature(callable_template, follow_wrapped=False)
    except ValueError:
        signature = None

    def with_sig_check(*args, **kwargs):
        if signature:
            try:
                signature.bind(*args, **kwargs)
            except TypeError as e:
                raise TypeError(
                    "{}, {}: {}".format(repr(template), repr(attr_name), str(e))
                )
        return value(*args, **kwargs)

    return with_sig_check


class UndefinedAttribute(BaseException):
    """
    Tentative access of an attribute from a StrictMock that is not defined yet.
    Inherits from BaseException to avoid being caught by tested code.
    """

    def __init__(self, strict_mock, name):
        super().__init__(strict_mock, name)
        self.strict_mock = strict_mock
        self.name = name

    def __str__(self):
        return (
            f"'{self.name}' is not set.\n"
            f"{self.strict_mock} must have a value set for this attribute "
            "if it is going to be accessed."
        )


class NonExistentAttribute(BaseException):
    """
    Tentative of setting of an attribute from a StrictMock that is not present
    at the template class.
    Inherits from BaseException to avoid being caught by tested code.
    """

    def __init__(self, strict_mock, name):
        super().__init__(strict_mock, name)
        self.strict_mock = strict_mock
        self.name = name

    def __str__(self):
        return (
            f"'{self.name}' can not be set.\n"
            f"{self.strict_mock} template class does not have this attribute "
            "so the mock can not have it as well.\n"
            "See also: 'runtime_attrs' at StrictMock.__init__."
        )


class NonCallableValue(BaseException):
    """
    Raised when trying to set a non callable value to a callable attribute of
    a StrictMock instance.
    """

    def __init__(self, strict_mock, name):
        super().__init__(strict_mock, name)
        self.strict_mock = strict_mock
        self.name = name

    def __str__(self):
        return (
            f"'{self.name}' can not be set with a non-callable value.\n"
            f"{self.strict_mock} template class requires this attribute to "
            "be callable."
        )


class StrictMock(object):
    """
    Mock object that won't allow any attribute access or method call, unless its
    behavior has been explicitly defined. This is meant to be a safer
    alternative to Python's standard Mock object, that will always return
    another mock when referred by default.

    StrictMock is "safe by default", meaning that it will never misbehave by
    lack of configuration. It will raise in the following situations:

    - Get/Set attribute that's not part of the specification (template or
      runtime_attrs).
    - Get attribute that is part of the specification, but has not yet been
      defined.
    - Call a method with different signature from the template.

    When appropriate, raised exceptions inherits from BaseException, in order to
    let exceptions raise the test, outside tested code, so we can get a clear
    signal of what is happening: either the mock is missing a required behavior
    or the tested code is misbehaving.
    """

    TRIM_PATH_PREFIX = ""

    def __new__(
        cls, template=None, runtime_attrs=None, name=None, default_context_manager=True
    ):
        if template:
            name = f"{template.__name__}{cls.__name__}"
        else:
            name = cls.__name__
        # Using a subclass per instance, we can use its dictionary to store
        # all instance attributes, so both regular and magic methods can
        # work.
        strict_mock_subclass = type(name, (cls,), {})
        strict_mock_instance = object.__new__(strict_mock_subclass)
        return strict_mock_instance

    def __init__(
        self, template=None, runtime_attrs=None, name=None, default_context_manager=True
    ):
        """
        template: Template class to be used as a template for the mock.
        runtime_attrs: Often attributes are created within an instance's
        lifecycle, typically from __init__(). To allow mocking such attributes,
        specify their names here.
        name: an optional name for this mock instance.
        default_context_manager: If the template class is a context manager,
        setup a mock for __enter__ that yields itself and an empty function
        for __exit__.
        """
        if template and not inspect.isclass(template):
            raise ValueError("Template must be a class.")
        self.__dict__["__template"] = template

        self.__dict__["__runtime_attrs"] = runtime_attrs or []
        self.__dict__["__name"] = name

        frameinfo = inspect.getframeinfo(inspect.stack()[1][0])
        filename = frameinfo.filename
        lineno = frameinfo.lineno
        if self.TRIM_PATH_PREFIX:
            split = filename.split(self.TRIM_PATH_PREFIX)
            if len(split) == 2 and not split[0]:
                filename = split[1]
        if os.path.exists(filename):
            self.__dict__["__caller"] = "{}:{}".format(filename, lineno)
        else:
            self.__dict__["__caller"] = None

        if (
            self.__template
            and default_context_manager
            and hasattr(self.__template, "__enter__")
            and hasattr(self.__template, "__exit__")
        ):
            self.__enter__ = lambda: self
            self.__exit__ = lambda exc_type, exc_value, traceback: None

    @property
    def __class__(self):
        return self.__template if self.__template is not None else type(self)

    @property
    def __template(self):
        import testslide.mock_constructor  # Avoid cyclic dependencies

        # If the template class was mocked with mock_constructor(), this will
        # return the mocked subclass, which contains all attributes we need for
        # introspection.
        return testslide.mock_constructor._get_class_or_mock(
            self.__dict__["__template"]
        )

    @property
    def __runtime_attrs(self):
        return self.__dict__["__runtime_attrs"]

    def __template_has_attr(self, name):
        def get_class_init(klass):
            import testslide.mock_constructor  # Avoid cyclic dependencies

            if testslide.mock_constructor._is_mocked_class(klass):
                # If klass is the mocked subclass, pull the original version of
                # __init__ so we can introspect into its implementation (and
                # not the __init__ wrapper at the mocked class).
                mocked_class = klass
                original_class = mocked_class.mro()[1]
                return testslide.mock_constructor._get_original_init(
                    original_class, instance=None, owner=mocked_class
                )
            else:
                return klass.__init__

        def is_runtime_attr():
            if self.__template:
                for klass in self.__template.mro():
                    template_init = get_class_init(klass)
                    if not inspect.isfunction(template_init):
                        continue
                    for instruction in dis.get_instructions(template_init):
                        if (
                            instruction.opname == "STORE_ATTR"
                            and name == instruction.argval
                        ):
                            return True
            return False

        return (
            hasattr(self.__template, name)
            or name in self.__runtime_attrs
            or name in getattr(self.__template, "__slots__", [])
            or is_runtime_attr()
        )

    def __setattr__(self, name, value):
        mock_value = value
        if self.__template:
            if not self.__template_has_attr(name):
                raise NonExistentAttribute(self, name)

            if hasattr(self.__template, name):
                # If we are working with a callable we need to actually
                # set the side effect of the callable, not directly assign
                # the value to the callable
                if callable(getattr(self.__template, name)):
                    if not callable(value):
                        raise NonCallableValue(self, name)
                    mock_value = staticmethod(
                        _add_signature_validation(value, self.__template, name)
                    )
        else:
            if callable(value):
                mock_value = staticmethod(value)

        setattr(type(self), name, mock_value)

    def __getattr__(self, name):
        if name in type(self).__dict__:
            return type(self).__dict__
        else:
            if self.__template and self.__template_has_attr(name):
                raise UndefinedAttribute(self, name)
            else:
                raise AttributeError(f"'{name}' was not set for {self}.")

    def __delattr__(self, name):
        if name in type(self).__dict__:
            delattr(type(self), name)

    def __repr__(self):
        template_str = (
            " template={}.{}".format(
                self.__template.__module__, self.__template.__name__
            )
            if self.__template
            else ""
        )

        if self.__dict__["__name"]:
            name_str = " name={}".format(repr(self.__dict__["__name"]))
        else:
            name_str = ""

        if self.__dict__["__caller"]:
            caller_str = " {}".format(self.__dict__["__caller"])
        else:
            caller_str = ""

        return "<StrictMock 0x{:02X}{name}{template}{caller}>".format(
            id(self), name=name_str, template=template_str, caller=caller_str
        )

    def __copy__(self):
        self_copy = type(self)(
            template=self.__template, runtime_attrs=self.__runtime_attrs
        )

        for name in type(self).__dict__:
            if name not in self_copy.__dict__:
                setattr(self_copy, name, type(self).__dict__[name])

        return self_copy

    def __deepcopy__(self, memo=None):
        if memo is None:
            memo = {}
        self_copy = type(self)(
            template=self.__template, runtime_attrs=self.__runtime_attrs
        )
        memo[id(self)] = self_copy
        for name in type(self).__dict__:
            if name not in self_copy.__dict__:
                setattr(self_copy, name, copy.deepcopy(type(self).__dict__[name], memo))
        return self_copy
