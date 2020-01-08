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
        if "_template" in template.__dict__:
            template = template._template
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

    def __init__(self, strict_mock, name, extra_msg=None):
        super().__init__(strict_mock, name)
        self.strict_mock = strict_mock
        self.name = name
        self.extra_msg = extra_msg

    def __str__(self):
        message = (
            f"'{self.name}' is not set.\n"
            f"{self.strict_mock} must have a value set for this attribute "
            "if it is going to be accessed."
        )
        if self.extra_msg is not None:
            message += f"\n{self.extra_msg}"
        return message


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


class NonAwaitableReturn(BaseException):
    """
    Raised when a coroutine method at a StrictMock is assigned a not coroutine
    callable function.
    """

    def __init__(self, strict_mock, name):
        super().__init__(strict_mock, name)
        self.strict_mock = strict_mock
        self.name = name

    def __str__(self):
        return (
            f"'{self.name}' can not be set with a callable that does not "
            "return an awaitable.\n"
            f"{self.strict_mock} template class requires this attribute to "
            "be a callable that returns an awaitable (eg: a 'async def' "
            "function)."
        )


class UnsupportedMagic(BaseException):
    """
    Raised when trying to set an unsupported magic attribute to a StrictMock
    instance.
    """

    def __init__(self, strict_mock, name):
        super().__init__(strict_mock, name)
        self.strict_mock = strict_mock
        self.name = name

    def __str__(self):
        return f"setting '{self.name}' is not supported."


class _DefaultMagic:
    CONTEXT_MANAGER_METHODS = ["__enter__", "__exit__", "__aenter__", "__aexit__"]

    def __init__(self, strict_mock, name):
        self.strict_mock = strict_mock
        self.name = name

    def __call__(self, *args, **kwargs):
        message = None
        if self.name in self.CONTEXT_MANAGER_METHODS:
            message = (
                "Tip: most context managers can be automatically configured "
                "with 'default_context_manager=True'."
            )
        raise UndefinedAttribute(self.strict_mock, self.name, message)

    def __copy__(self):
        return type(self)(strict_mock=self.strict_mock, name=self.name)

    def __deepcopy__(self, memo=None):
        if memo is None:
            memo = {}
        self_copy = type(self)(strict_mock=self.strict_mock, name=self.name)
        memo[id(self)] = self_copy
        return self_copy


class _MethodProxy(object):
    """
    When setting callable attributes, the new value is wrapped by another
    function that does signature and async validations. We then need this proxy
    around it, so that when the attribute is called, the mock value is called
    (the wrapper function which then calls the new value) but all attribute
    access is forwarded to the new value.
    """

    def __init__(self, value, callable_value=None):
        self.__dict__["_value"] = value
        self.__dict__["_callable_value"] = callable_value if callable_value else value

    def __get__(self, instance, owner=None):
        if self.__dict__["_value"] is self.__dict__["_callable_value"]:
            return self.__dict__["_callable_value"]
        else:
            return self

    def __getattr__(self, name):
        return getattr(self.__dict__["_value"], name)

    def __setattr__(self, name, value):
        return setattr(self.__dict__["_value"], name, value)

    def __delattr__(self, name):
        return delattr(self.__dict__["_value"], name)

    def __call__(self, *args, **kwargs):
        return self.__dict__["_callable_value"](*args, **kwargs)

    def __copy__(self):
        return type(self)(
            callable_value=self.__dict__["_callable_value"],
            value=self.__dict__["_value"],
        )

    def __deepcopy__(self, memo=None):
        if memo is None:
            memo = {}
        self_copy = type(self)(
            callable_value=copy.deepcopy(self.__dict__["_callable_value"]),
            value=copy.deepcopy(self.__dict__["_value"]),
        )
        memo[id(self)] = self_copy
        return self_copy


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

    # All of these magic should be OK to be set at the mock and they are
    # expected to work as they should. If implemented by the template class,
    # they will have default values assigned to them, that raise
    # UndefinedAttribute until configured.
    _SETTABLE_MAGICS = [
        "__abs__",
        "__add__",
        "__aenter__",
        "__aexit__",
        "__aiter__",
        "__and__",
        "__anext__",
        "__await__",
        "__bool__",
        "__bytes__",
        "__call__",
        "__ceil__",
        "__complex__",
        "__contains__",
        "__delete__",
        "__delitem__",
        "__divmod__",
        "__enter__",
        "__enter__",
        "__eq__",
        "__exit__",
        "__exit__",
        "__float__",
        "__floor__",
        "__floordiv__",
        "__format__",
        "__ge__",
        "__get__",
        "__getformat__",
        "__getinitargs__",
        "__getitem__",
        "__getnewargs__",
        "__getnewargs_ex__",
        "__getstate__",
        "__gt__",
        "__iadd__",
        "__iand__",
        "__ifloordiv__",
        "__ilshift__",
        "__imatmul__",
        "__imod__",
        "__imul__",
        "__index__",
        "__instancecheck__",
        "__int__",
        "__invert__",
        "__ior__",
        "__ipow__",
        "__irshift__",
        "__isub__",
        "__iter__",
        "__iter__",
        "__iter__",
        "__itruediv__",
        "__ixor__",
        "__le__",
        "__len__",
        "__length_hint__",
        "__lshift__",
        "__lt__",
        "__matmul__",
        "__missing__",
        "__mod__",
        "__mul__",
        "__name__",
        "__ne__",
        "__neg__",
        "__next__",
        "__or__",
        "__pos__",
        "__pow__",
        "__qualname__",
        "__radd__",
        "__rand__",
        "__rdivmod__",
        "__reduce__",
        "__reduce_ex__",
        "__repr__",
        "__reversed__",
        "__rfloordiv__",
        "__rlshift__",
        "__rmatmul__",
        "__rmod__",
        "__rmul__",
        "__ror__",
        "__round__",
        "__rpow__",
        "__rrshift__",
        "__rshift__",
        "__rsub__",
        "__rtruediv__",
        "__rxor__",
        "__set__",
        "__set_name__",
        "__setformat__",
        "__setitem__",
        "__setstate__",
        "__sizeof__",
        "__str__",
        "__sub__",
        "__subclasscheck__",
        "__truediv__",
        "__trunc__",
        "__xor__",
    ]

    # These magics either won't work or makes no sense to be set for mock after
    # an instance of a class. Trying to set them will raise UnsupportedMagic.
    _UNSETTABLE_MAGICS = [
        "__bases__",
        "__class__",
        "__class_getitem__",
        "__copy__",
        "__deepcopy__",
        "__del__",
        "__delattr__",
        "__dict__",
        "__dir__",
        "__getattr__",
        "__getattribute__",
        "__hash__",
        "__init__",
        "__init_subclass__",
        "__mro__",
        "__new__",
        "__setattr__",
        "__slots__",
        "__subclasses__",
    ]

    def __new__(
        cls,
        template=None,
        runtime_attrs=None,
        name=None,
        default_context_manager=False,
        signature_validation=True,
    ):
        """
        For every new instance of StrictMock we dynamically create a subclass of
        StrictMock and return an instance of it. This allows us to use this new
        subclass dictionary for all attributes, including magic ones, that must
        be defined at the class to work.
        """
        if template:
            name = f"{template.__name__}{cls.__name__}"
        else:
            name = cls.__name__
        strict_mock_subclass = type(name, (cls,), {})
        strict_mock_instance = object.__new__(strict_mock_subclass)
        return strict_mock_instance

    def _setup_magic_methods(self):
        """
        Populate all template's magic methods with expected default behavior.
        This is important as things such as bool() depend on they existing
        on the object's class __dict__.
        https://github.com/facebookincubator/TestSlide/issues/23
        """
        if not self._template:
            return

        implemented_magic_methods = []
        for klass in type(self).mro():
            if klass is object:
                continue
            for name in klass.__dict__:
                if name.startswith("__") and name.endswith("__"):
                    implemented_magic_methods.append(name)

        for klass in self._template.mro():
            if klass is object:
                continue
            for name in klass.__dict__:
                if (
                    callable(klass.__dict__[name])
                    and name in self._SETTABLE_MAGICS
                    and name not in self._UNSETTABLE_MAGICS
                    and name not in implemented_magic_methods
                ):
                    setattr(self, name, _DefaultMagic(self, name))

    def _setup_default_context_manager(self, default_context_manager):
        if self._template and default_context_manager:
            if hasattr(self._template, "__enter__") and hasattr(
                self._template, "__exit__"
            ):
                self.__enter__ = lambda: self
                self.__exit__ = lambda exc_type, exc_value, traceback: None
            if hasattr(self._template, "__aenter__") and hasattr(
                self._template, "__aexit__"
            ):

                async def aenter():
                    return self

                async def aexit(exc_type, exc_value, traceback):
                    pass

                self.__aenter__ = aenter
                self.__aexit__ = aexit

    def _get_caller(self, depth):
        frameinfo = inspect.getframeinfo(inspect.stack()[depth + 1][0])
        filename = frameinfo.filename
        lineno = frameinfo.lineno
        if self.TRIM_PATH_PREFIX:
            split = filename.split(self.TRIM_PATH_PREFIX)
            if len(split) == 2 and not split[0]:
                filename = split[1]
        if os.path.exists(filename):
            return "{}:{}".format(filename, lineno)
        else:
            return None

    def __init__(
        self,
        template=None,
        runtime_attrs=None,
        name=None,
        default_context_manager=False,
        signature_validation=True,
    ):
        """
        template: Template class to be used as a template for the mock.
        runtime_attrs: Often attributes are created within an instance's
        lifecycle, typically from __init__(). To allow mocking such attributes,
        specify their names here.
        name: an optional name for this mock instance.
        default_context_manager: If the template class is a context manager,
        setup a mock for __enter__/__aenter__ that yields itself and an empty function
        for __exit__/__aexit__.
        signature_validation: validate callable attributes calls against the
        template's method signature, raising TypeError if they don't match. This
        is accomplished by wrapping the callable attribute with another
        function. While attribute access is proxied correctly, the type() of
        the attribute will change. Setting this value to False disables
        signature validation, and should only be used when type() is required
        to not change.
        """
        if template and not inspect.isclass(template):
            raise ValueError("Template must be a class.")
        self.__dict__["_template"] = template

        self.__dict__["_runtime_attrs"] = runtime_attrs or []
        self.__dict__["_name"] = name
        self.__dict__["_signature_validation"] = signature_validation
        self.__dict__["__caller"] = self._get_caller(1)

        self._setup_magic_methods()

        self._setup_default_context_manager(default_context_manager)

    @property
    def __class__(self):
        return self._template if self._template is not None else type(self)

    @property
    def _template(self):
        import testslide.mock_constructor  # Avoid cyclic dependencies

        # If the template class was mocked with mock_constructor(), this will
        # return the mocked subclass, which contains all attributes we need for
        # introspection.
        return testslide.mock_constructor._get_class_or_mock(self.__dict__["_template"])

    @property
    def _runtime_attrs(self):
        return self.__dict__["_runtime_attrs"]

    def _template_has_attr(self, name):
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
            if self._template:
                for klass in self._template.mro():
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
            hasattr(self._template, name)
            or name in self._runtime_attrs
            or name in getattr(self._template, "__slots__", [])
            or is_runtime_attr()
        )

    @staticmethod
    def _is_magic_method(name):
        return name.startswith("__") and name.endswith("__")

    def __setattr__(self, name, value):
        if self._is_magic_method(name):
            # ...check whether we're allowed to mock...
            if name in self._UNSETTABLE_MAGICS or (
                name in StrictMock.__dict__ and name not in self._SETTABLE_MAGICS
            ):
                raise UnsupportedMagic(self, name)
            # ...or if it is something unsupported.
            if name not in self._SETTABLE_MAGICS:
                raise NotImplementedError(
                    f"StrictMock does not implement support for {name}"
                )

        mock_value = value
        if self._template:
            if not self._template_has_attr(name):
                raise NonExistentAttribute(self, name)

            if hasattr(self._template, name):
                template_value = getattr(self._template, name)
                if callable(template_value):
                    if not callable(value):
                        raise NonCallableValue(self, name)

                    if self.__dict__["_signature_validation"]:
                        signature_validation_wrapper = _add_signature_validation(
                            value, self._template, name
                        )
                        if inspect.iscoroutinefunction(template_value):

                            async def awaitable_return_validation_wrapper(
                                *args, **kwargs
                            ):
                                return_value = signature_validation_wrapper(
                                    *args, **kwargs
                                )
                                if not inspect.isawaitable(return_value):
                                    raise NonAwaitableReturn(self, name)
                                return await return_value

                            callable_value = awaitable_return_validation_wrapper
                        else:
                            callable_value = signature_validation_wrapper
                    else:
                        callable_value = None
                    mock_value = _MethodProxy(
                        value=value, callable_value=callable_value
                    )
            else:
                if callable(value):
                    # We don't really need the proxy here, but it serves the
                    # double purpose of swallowing self / cls when needed.
                    mock_value = _MethodProxy(value=value)
        else:
            if callable(value):
                # We don't really need the proxy here, but it serves the
                # double purpose of swallowing self / cls when needed.
                mock_value = _MethodProxy(value=value)

        setattr(type(self), name, mock_value)

    def __getattr__(self, name):
        if self._template and self._template_has_attr(name):
            raise UndefinedAttribute(self, name)
        else:
            raise AttributeError(f"'{name}' was not set for {self}.")

    def __delattr__(self, name):
        if name in type(self).__dict__:
            delattr(type(self), name)

    def __repr__(self):
        template_str = (
            " template={}.{}".format(self._template.__module__, self._template.__name__)
            if self._template
            else ""
        )

        if self.__dict__["_name"]:
            name_str = " name={}".format(repr(self.__dict__["_name"]))
        else:
            name_str = ""

        if self.__dict__["__caller"]:
            caller_str = " {}".format(self.__dict__["__caller"])
        else:
            caller_str = ""

        return "<StrictMock 0x{:02X}{name}{template}{caller}>".format(
            id(self), name=name_str, template=template_str, caller=caller_str
        )

    def __str__(self):
        return self.__repr__()

    def _get_copy(self):
        self_copy = type(self)(
            template=self._template,
            runtime_attrs=self._runtime_attrs,
            name=self._name,
            signature_validation=self._signature_validation,
        )
        self_copy.__dict__["__caller"] = self._get_caller(2)
        return self_copy

    def _get_copyable_attrs(self, self_copy):
        attrs = []
        for name in type(self).__dict__:
            if name not in self_copy.__dict__:
                if (
                    name.startswith("__")
                    and name.endswith("__")
                    and not name in self._SETTABLE_MAGICS
                ):
                    continue
                attrs.append(name)
        return attrs

    def __copy__(self):
        self_copy = self._get_copy()

        for name in self._get_copyable_attrs(self_copy):
            setattr(type(self_copy), name, type(self).__dict__[name])

        return self_copy

    def __deepcopy__(self, memo=None):
        if memo is None:
            memo = {}
        self_copy = self._get_copy()
        memo[id(self)] = self_copy

        for name in self._get_copyable_attrs(self_copy):
            value = copy.deepcopy(type(self).__dict__[name], memo)
            setattr(type(self_copy), name, value)
        return self_copy
