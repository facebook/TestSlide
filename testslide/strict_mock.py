# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.
import copy
import dis
import inspect
import os.path
from types import FrameType
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Type,
    Union,
    get_type_hints,
)

import testslide.lib
import testslide.mock_callable

if TYPE_CHECKING:
    # Hack to enable typing information for mypy
    from testslide.mock_callable import _CallableMock, _YieldValuesRunner  # noqa: F401


class UndefinedAttribute(BaseException):
    """
    Tentative access of an attribute from a StrictMock that is not defined yet.
    Inherits from BaseException to avoid being caught by tested code.
    """

    def __init__(
        self, strict_mock: "StrictMock", name: str, extra_msg: Optional[str] = None
    ) -> None:
        super().__init__(strict_mock, name)
        self.strict_mock = strict_mock
        self.name = name
        self.extra_msg = extra_msg

    def __str__(self) -> str:
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

    def __init__(self, strict_mock: "StrictMock", name: str) -> None:
        super().__init__(strict_mock, name)
        self.strict_mock = strict_mock
        self.name = name

    def __str__(self) -> str:
        return (
            f"'{self.name}' is not part of the API.\n"
            f"{self.strict_mock} template class API does not have this "
            "attribute so the mock can not have it as well.\n"
            "If you are inheriting StrictMock, you can define private "
            "attributes, that will not interfere with the API, by prefixing "
            "them with '__' (and at most one '_' suffix) "
            " (https://docs.python.org/3/tutorial/classes.html#tut-private).\n"
            "See also: 'runtime_attrs' at StrictMock.__init__."
        )


class NonCallableValue(BaseException):
    """
    Raised when trying to set a non callable value to a callable attribute of
    a StrictMock instance.
    """

    def __init__(self, strict_mock: "StrictMock", name: str) -> None:
        super().__init__(strict_mock, name)
        self.strict_mock = strict_mock
        self.name = name

    def __str__(self) -> str:
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

    def __init__(self, strict_mock: "StrictMock", name: str) -> None:
        super().__init__(strict_mock, name)
        self.strict_mock = strict_mock
        self.name = name

    def __str__(self) -> str:
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

    def __init__(self, strict_mock: "StrictMock", name: str) -> None:
        super().__init__(strict_mock, name)
        self.strict_mock = strict_mock
        self.name = name

    def __str__(self) -> str:
        return f"setting '{self.name}' is not supported."


class _DefaultMagic:
    CONTEXT_MANAGER_METHODS = ["__enter__", "__exit__", "__aenter__", "__aexit__"]

    def __init__(self, strict_mock: "StrictMock", name: str):
        self.strict_mock = strict_mock
        self.name = name

    def __call__(self, *args: Any, **kwargs: Any) -> None:
        message = None
        if self.name in self.CONTEXT_MANAGER_METHODS:
            message = (
                "Tip: most context managers can be automatically configured "
                "with 'default_context_manager=True'."
            )
        raise UndefinedAttribute(self.strict_mock, self.name, message)

    def __copy__(self) -> "_DefaultMagic":
        return type(self)(strict_mock=self.strict_mock, name=self.name)

    def __deepcopy__(self, memo: Optional[Dict[Any, Any]] = None) -> "_DefaultMagic":
        if memo is None:
            memo = {}
        self_copy = type(self)(strict_mock=self.strict_mock, name=self.name)
        memo[id(self)] = self_copy
        return self_copy


class _MethodProxy:
    """
    When setting callable attributes, the new value is wrapped by another
    function that does signature and async validations. We then need this proxy
    around it, so that when the attribute is called, the mock value is called
    (the wrapper function which then calls the new value) but all attribute
    access is forwarded to the new value.
    """

    def __init__(self, value: Any, callable_value: Optional[Callable] = None) -> None:
        self.__dict__["_value"] = value
        self.__dict__["_callable_value"] = callable_value if callable_value else value

    def __get__(
        self, instance: "StrictMock", owner: Optional[Type["StrictMock"]] = None
    ) -> Union[object, Callable]:
        if self.__dict__["_value"] is self.__dict__["_callable_value"]:
            return self.__dict__["_callable_value"]
        else:
            return self

    def __getattr__(self, name: str) -> str:
        return getattr(self.__dict__["_value"], name)

    def __setattr__(self, name: str, value: str) -> None:
        return setattr(self.__dict__["_value"], name, value)

    def __delattr__(self, name: str) -> None:
        return delattr(self.__dict__["_value"], name)

    def __call__(self, *args: Any, **kwargs: Any) -> Optional[Any]:
        return self.__dict__["_callable_value"](*args, **kwargs)

    def __copy__(self) -> "_MethodProxy":
        return type(self)(
            callable_value=self.__dict__["_callable_value"],
            value=self.__dict__["_value"],
        )

    def __deepcopy__(self, memo: Optional[Dict[Any, Any]] = None) -> "_MethodProxy":
        if memo is None:
            memo = {}
        self_copy = type(self)(
            callable_value=copy.deepcopy(self.__dict__["_callable_value"]),
            value=copy.deepcopy(self.__dict__["_value"]),
        )
        memo[id(self)] = self_copy
        return self_copy

    def __repr__(self) -> str:
        # Override repr to have a representation that provides information
        # about the wrapped method
        return repr(self.__dict__["_value"])


class StrictMock:
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
    __SETTABLE_MAGICS = [
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
    __UNSETTABLE_MAGICS = [
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
        template: Optional[type] = None,
        runtime_attrs: Optional[List[Any]] = None,
        name: Optional[str] = None,
        default_context_manager: bool = False,
        type_validation: bool = True,
        attributes_to_skip_type_validation: List[str] = [],
    ) -> "StrictMock":
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

    def __setup_magic_methods(self) -> None:
        """
        Populate all template's magic methods with expected default behavior.
        This is important as things such as bool() depend on they existing
        on the object's class __dict__.
        https://github.com/facebook/TestSlide/issues/23
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
                if name in type(self).__dict__:
                    continue
                if name == "__hash__":
                    if klass.__dict__["__hash__"] is None:
                        setattr(self, name, None)
                    else:
                        setattr(self, name, lambda: id(self))
                    continue
                if (
                    callable(klass.__dict__[name])
                    and name in self.__SETTABLE_MAGICS
                    and name not in self.__UNSETTABLE_MAGICS
                    and name not in implemented_magic_methods
                ):
                    setattr(self, name, _DefaultMagic(self, name))

    def __setup_default_context_manager(self, default_context_manager: bool) -> None:
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

    def __get_caller_frame(self, depth: int) -> FrameType:
        # Adding extra 3 to account for the stack:
        #   __get_caller_frame
        #   __get_caller
        #   __init__
        depth = depth + 3
        current_frame = inspect.currentframe()
        while current_frame:
            depth -= 1
            if not depth:
                break

            current_frame = current_frame.f_back

        return current_frame  # type: ignore

    def __get_caller(self, depth: int) -> Optional[str]:
        # Doing inspect.stack will retrieve the whole stack, including context
        # and that is really slow, this only retrieves the minimum, and does
        # not read the file contents.
        caller_frame = self.__get_caller_frame(depth)
        # loading the context ends up reading files from disk and that might block
        # the event loop, so we don't do it.
        frameinfo = inspect.getframeinfo(caller_frame, context=0)
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

    def __setup_subclass(self):
        """
        When StrictMock is subclassed, any attributes defined at the subclass
        will override any of StrictMock's validations. In order to overcome
        this, for attributes that makes sense, we set them at StrictMock's
        dynamically created subclass from __new__ using __setattr__, so that
        all validations work.
        """
        if type(self).mro()[1] == StrictMock:
            return
        for klass in type(self).mro()[1:]:
            if klass == StrictMock:
                break
            for name in klass.__dict__.keys():
                if name in [
                    "__doc__",
                    "__init__",
                    "__module__",
                ]:
                    continue
                # https://docs.python.org/3/tutorial/classes.html#tut-private
                if name.startswith(f"_{type(self).__name__}__") and not name.endswith(
                    "__"
                ):
                    continue
                if name == "__hash__" and klass.__dict__["__hash__"] is None:
                    continue
                StrictMock.__setattr__(self, name, getattr(self, name))

    def __init__(
        self,
        template: Optional[type] = None,
        runtime_attrs: Optional[List[Any]] = None,
        name: Optional[str] = None,
        default_context_manager: bool = False,
        type_validation: bool = True,
        attributes_to_skip_type_validation: List[str] = [],
    ) -> None:
        """
        template: Template class to be used as a template for the mock.
        runtime_attrs: Often attributes are created within an instance's
        lifecycle, typically from __init__(). To allow mocking such attributes,
        specify their names here.
        name: an optional name for this mock instance.
        default_context_manager: If the template class is a context manager,
        setup a mock for __enter__/__aenter__ that yields itself and an empty function
        for __exit__/__aexit__.
        type_validation: validate callable attributes calls against the
        template's method signature and use type hinting information from template
        to validate that mock attribute types match them. Type validation also
        happens forcallable attributes (instance/static/class methods) calls.
        _attributes_to_skip_type_validation: do not validate type for these attributes
        of the strictmock instance.
        """
        if template is not None and not inspect.isclass(template):
            raise ValueError("Template must be a class.")
        self.__dict__["_template"] = template

        self.__dict__["_runtime_attrs"] = runtime_attrs or []
        self.__dict__["_name"] = name
        self.__dict__["_type_validation"] = type_validation
        self.__dict__["__caller"] = self.__get_caller(1)
        self.__dict__[
            "_attributes_to_skip_type_validation"
        ] = attributes_to_skip_type_validation

        caller_frame = inspect.currentframe().f_back  # type: ignore
        # loading the context ends up reading files from disk and that might block
        # the event loop, so we don't do it.
        caller_frame_info = inspect.getframeinfo(caller_frame, context=0)  # type: ignore
        self.__dict__["_caller_frame_info"] = caller_frame_info

        self.__setup_magic_methods()

        self.__setup_default_context_manager(default_context_manager)

        self.__setup_subclass()

    @property  # type: ignore
    def __class__(self) -> type:
        return self._template if self._template is not None else type(self)

    @property
    def _template(self) -> None:
        import testslide.mock_constructor  # Avoid cyclic dependencies

        # If the template class was mocked with mock_constructor(), this will
        # return the mocked subclass, which contains all attributes we need for
        # introspection.
        return testslide.mock_constructor._get_class_or_mock(self.__dict__["_template"])

    # FIXME change to __runtime_attrs
    @property
    def _runtime_attrs(self) -> Optional[List[Any]]:
        return self.__dict__["_runtime_attrs"]

    def __template_has_attr(self, name: str) -> bool:
        def get_class_init(klass: type) -> Callable:
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
                return klass.__init__  # type: ignore

        def is_runtime_attr() -> bool:
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
            or name in self._runtime_attrs  # type: ignore
            or name in getattr(self._template, "__slots__", [])
            or is_runtime_attr()
        )

    @staticmethod
    def __is_magic_method(name: str) -> bool:
        return name.startswith("__") and name.endswith("__")

    def __validate_attribute_type(self, name: str, value: Any) -> None:
        if (
            not self.__dict__["_type_validation"]
            or name in self.__dict__["_attributes_to_skip_type_validation"]
        ):
            return

        if self._template is not None:
            try:
                annotations = get_type_hints(self._template)
            except Exception:
                # Some modules can throw KeyError : https://bugs.python.org/issue41515
                annotations = {}
            if name in annotations:
                testslide.lib._validate_argument_type(annotations[name], name, value)

    def __validate_and_wrap_mock_value(self, name: str, value: Any) -> Any:
        if self._template:
            if not self.__template_has_attr(name):
                if not (
                    name.startswith(f"_{type(self).__name__}__")
                    and not name.endswith("__")
                ):
                    raise NonExistentAttribute(self, name)

            self.__validate_attribute_type(name, value)

            if hasattr(self._template, name):
                template_value = getattr(self._template, name)
                if callable(template_value):
                    if not callable(value):
                        raise NonCallableValue(self, name)
                    if self.__dict__["_type_validation"]:
                        signature_validation_wrapper = (
                            testslide.lib._wrap_signature_and_type_validation(
                                value,
                                self._template,
                                name,
                                self.__dict__["_type_validation"],
                            )
                        )

                        if inspect.iscoroutinefunction(template_value):

                            async def awaitable_return_validation_wrapper(
                                *args, **kwargs
                            ):
                                result_awaitable = signature_validation_wrapper(
                                    *args, **kwargs
                                )
                                if not inspect.isawaitable(result_awaitable):
                                    raise NonAwaitableReturn(self, name)

                                return_value = await result_awaitable
                                if not testslide.lib._is_wrapped_for_signature_and_type_validation(
                                    # The original value was already wrapped for type
                                    # validation. Skipping additional validation to
                                    # allow, for example, mock_callable to disable
                                    # validation for a very specific mock call rather
                                    # for the whole StrictMock instance
                                    value
                                ) and not isinstance(
                                    # If the return value is a _BaseRunner then type
                                    # validation, if needed, has already been performed
                                    return_value,
                                    testslide.mock_callable._BaseRunner,
                                ):
                                    testslide.lib._validate_return_type(
                                        template_value,
                                        return_value,
                                        self.__dict__["_caller_frame_info"],
                                    )
                                return return_value

                            callable_value = awaitable_return_validation_wrapper
                        else:

                            def return_validation_wrapper(*args, **kwargs):
                                return_value = signature_validation_wrapper(
                                    *args, **kwargs
                                )
                                if not testslide.lib._is_wrapped_for_signature_and_type_validation(
                                    # The original value was already wrapped for type
                                    # validation. Skipping additional validation to
                                    # allow, for example, mock_callable to disable
                                    # validation for a very specific mock call rather
                                    # for the whole StrictMock instance
                                    value
                                ) and not isinstance(
                                    # If the return value is a _BaseRunner then type
                                    # validation, if needed, has already been performed
                                    return_value,
                                    testslide.mock_callable._BaseRunner,
                                ):
                                    testslide.lib._validate_return_type(
                                        template_value,
                                        return_value,
                                        self.__dict__["_caller_frame_info"],
                                    )
                                return return_value

                            callable_value = return_validation_wrapper
                    else:
                        callable_value = None
                    return _MethodProxy(value=value, callable_value=callable_value)
            else:
                if callable(value):
                    # We don't really need the proxy here, but it serves the
                    # double purpose of swallowing self / cls when needed.
                    return _MethodProxy(value=value)
        else:
            if callable(value):
                # We don't really need the proxy here, but it serves the
                # double purpose of swallowing self / cls when needed.
                return _MethodProxy(value=value)

        return value

    def __setattr__(self, name: str, value: Any) -> None:
        if self.__is_magic_method(name):
            # ...check whether we're allowed to mock...
            if (
                name in self.__UNSETTABLE_MAGICS
                or (name in StrictMock.__dict__ and name not in self.__SETTABLE_MAGICS)
            ) and name != "__hash__":
                raise UnsupportedMagic(self, name)
            # ...or if it is something unsupported.
            if name not in self.__SETTABLE_MAGICS and name != "__hash__":
                raise NotImplementedError(
                    f"StrictMock does not implement support for {name}"
                )
            if name == "__hash__" and name in type(self).__dict__:
                raise UnsupportedMagic(self, name)

        mock_value = self.__validate_and_wrap_mock_value(name, value)
        setattr(type(self), name, mock_value)

    def __getattr__(self, name: str) -> Any:
        if self._template and self.__template_has_attr(name):
            raise UndefinedAttribute(self, name)
        else:
            raise AttributeError(f"'{name}' was not set for {self}.")

    def __delattr__(self, name: str) -> None:
        if name in type(self).__dict__:
            delattr(type(self), name)

    def __repr__(self) -> str:
        template_str = (
            " template={}.{}".format(self._template.__module__, self._template.__name__)  # type: ignore
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

    def __str__(self) -> str:
        return self.__repr__()

    def __get_copy(self) -> "StrictMock":
        self_copy = StrictMock(
            template=self._template,
            runtime_attrs=self._runtime_attrs,
            name=self._name,
            type_validation=self._type_validation,
            attributes_to_skip_type_validation=self._attributes_to_skip_type_validation,
        )
        self_copy.__dict__["__caller"] = self.__get_caller(2)
        return self_copy

    def __get_copyable_attrs(self, self_copy: "StrictMock") -> List[str]:
        attrs = []
        for name in type(self).__dict__:
            if name not in self_copy.__dict__:
                if (
                    name.startswith("__")
                    and name.endswith("__")
                    and name not in self.__SETTABLE_MAGICS
                ):
                    continue
                attrs.append(name)
        return attrs

    def __copy__(self) -> "StrictMock":
        self_copy = self.__get_copy()

        for name in self.__get_copyable_attrs(self_copy):
            setattr(type(self_copy), name, type(self).__dict__[name])

        return self_copy

    def __deepcopy__(self, memo: Optional[Dict[Any, Any]] = None) -> "StrictMock":
        if memo is None:
            memo = {}
        self_copy = self.__get_copy()
        memo[id(self)] = self_copy

        for name in self.__get_copyable_attrs(self_copy):
            value = copy.deepcopy(type(self).__dict__[name], memo)
            setattr(type(self_copy), name, value)
        return self_copy


def _extract_StrictMock_template(mock_obj: StrictMock) -> Optional[Any]:
    if "_template" in mock_obj.__dict__ and mock_obj._template is not None:
        return mock_obj._template

    return None


testslide.lib.MOCK_TEMPLATE_EXTRACTORS[StrictMock] = _extract_StrictMock_template  # type: ignore
