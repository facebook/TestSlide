# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

# pyre-unsafe

from types import TracebackType
from typing import Any, Optional

# In Cinder tests, imports are lazy. We use time.time() while profiling the imports.
# If the first time we call time.time() is inside the profiling, then we will import
# it there, which means we will profile the time import itself. This causes an
# infinite loop. Wrapping imports in Cinder eagerly imports it.
# Place any required imports here.
try:
    import time
except Exception:
    pass


class ImportedModule:
    """
    A module that was imported with __import__.
    """

    def __init__(
        self,
        name: str,
        globals: dict[str, Any] | None,
        level: int,
        parent: Optional["ImportedModule"] = None,
    ) -> None:
        self.name = name
        self.globals = globals
        self.level = level
        self.parent = parent
        self.children: list["ImportedModule"] = []
        self.time: float = 0
        if parent:
            parent.children.append(self)

    def __eq__(self, value: "ImportedModule") -> bool:  # type: ignore
        return str(self) == str(value)

    @property
    def all_children(self) -> list["ImportedModule"]:
        children = []

        for child in self.children:
            children.append(child)
            children.extend(child.all_children)

        return children

    @property
    def own_time(self) -> float:
        """
        How many seconds it took to import this module, minus all child imports.
        """
        return self.time - sum(child.time for child in self.children)

    def __str__(self) -> str:
        if self.globals and self.level:
            if self.level == 1:
                # pyre-fixme[16]: `Optional` has no attribute `__getitem__`.
                prefix = self.globals["__package__"]
            else:
                end = -1 * (self.level - 1)
                prefix = ".".join(self.globals["__package__"].split(".")[:end]) + "."
        else:
            prefix = ""
        return f"{prefix}{self.name}"

    def __enter__(self) -> None:
        # pyre-fixme[16]: `ImportedModule` has no attribute `_start_time`.
        self._start_time = time.time()

    def __exit__(
        self,
        exc_type: type | None,
        exc_val: Exception | None,
        exc_tb: TracebackType,
    ) -> None:
        # pyre-fixme[16]: `ImportedModule` has no attribute `_start_time`.
        self.time = time.time() - self._start_time


class ImportProfiler:
    """
    Experimental!

    Quick'n dirty profiler for module import times.

    Usage:

        from testslide.import_profiler import ImportProfiler

        with ImportProfiler() as import_profiler:
            import everything.here

        import_profiler.print_stats(100)

    This will print the dependency tree for imported modules that took more than 100ms
    to be imported.
    """

    def __init__(self) -> None:
        self._original_import = __builtins__["__import__"]  # type: ignore

    def __enter__(self) -> "ImportProfiler":
        __builtins__["__import__"] = self._profiled_import  # type:ignore
        # pyre-fixme[16]: `ImportProfiler` has no attribute `_top_imp_modules`.
        self._top_imp_modules: list[ImportedModule] = []
        # pyre-fixme[16]: `ImportProfiler` has no attribute `_import_stack`.
        self._import_stack: list[ImportedModule] = []
        # pyre-fixme[16]: `ImportProfiler` has no attribute `total_time`.
        self.total_time: float = 0
        # pyre-fixme[16]: `ImportProfiler` has no attribute `_start_time`.
        self._start_time = time.time()
        return self

    def __exit__(
        self,
        exc_type: type | None,
        exc_val: Exception | None,
        exc_tb: TracebackType | None,
    ) -> None:
        # pyre-fixme[16]: `ImportProfiler` has no attribute `total_time`.
        # pyre-fixme[16]: `ImportProfiler` has no attribute `_start_time`.
        self.total_time = time.time() - self._start_time
        __builtins__["__import__"] = self._original_import  # type:ignore

    # def _profiled_import(self, name, globals=None, locals=None, fromlist=(), level=0):
    def _profiled_import(
        self,
        name: str,
        globals: dict[str, Any] | None = None,
        locals: dict[str, Any] | None = None,
        fromlist: tuple = (),
        level: int = 0,
    ) -> None:
        # print('Importing {}'.format(repr(name)))
        imp_mod = ImportedModule(
            name=name,
            globals=globals,
            level=level,
            # pyre-fixme[16]: `ImportProfiler` has no attribute `_import_stack`.
            parent=self._import_stack[-1] if self._import_stack else None,
        )
        if not self._import_stack:
            # pyre-fixme[16]: `ImportProfiler` has no attribute `_top_imp_modules`.
            self._top_imp_modules.append(imp_mod)
        self._import_stack.append(imp_mod)
        with imp_mod:
            try:
                return self._original_import(name, globals, locals, fromlist, level)
            finally:
                self._import_stack.pop()

    def print_stats(self, threshold_ms: int = 0) -> None:
        def print_imp_mod(imp_mod: ImportedModule, indent: int = 0) -> None:
            own_ms = int(imp_mod.own_time * 1000)
            if own_ms >= threshold_ms or any(
                child
                for child in imp_mod.all_children
                if child.own_time * 1000 >= threshold_ms
            ):
                print("{}{}: {}ms".format("  " * indent, imp_mod, own_ms))
            for child_imp_mod in imp_mod.children:
                print_imp_mod(child_imp_mod, indent + 1)

        # pyre-fixme[16]: `ImportProfiler` has no attribute `_top_imp_modules`.
        for imp_mod in self._top_imp_modules:
            print_imp_mod(imp_mod)
        print()
        # pyre-fixme[16]: `ImportProfiler` has no attribute `total_time`.
        print(f"Total import time: {int(self.total_time * 1000)}ms")
