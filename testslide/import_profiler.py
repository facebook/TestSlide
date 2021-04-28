# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import time
from types import TracebackType
from typing import Any, Dict, List, Optional, Tuple


class ImportedModule:
    """
    A module that was imported with __import__.
    """

    def __init__(
        self,
        name: str,
        globals: Optional[Dict[str, Any]],
        level: int,
        parent: Optional["ImportedModule"] = None,
    ) -> None:
        self.name = name
        self.globals = globals
        self.level = level
        self.parent = parent
        self.children: List["ImportedModule"] = []
        self.time: float = 0
        if parent:
            parent.children.append(self)

    def __eq__(self, value: "ImportedModule") -> bool:  # type: ignore
        return str(self) == str(value)

    @property
    def all_children(self) -> List["ImportedModule"]:
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
                prefix = self.globals["__package__"]
            else:
                end = -1 * (self.level - 1)
                prefix = ".".join(self.globals["__package__"].split(".")[:end]) + "."
        else:
            prefix = ""
        return "{}{}".format(prefix, self.name)

    def __enter__(self) -> None:
        self._start_time = time.time()

    def __exit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[Exception],
        exc_tb: TracebackType,
    ) -> None:
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
        self._top_imp_modules: List[ImportedModule] = []
        self._import_stack: List[ImportedModule] = []
        self.total_time: float = 0
        self._start_time = time.time()
        return self

    def __exit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[Exception],
        exc_tb: Optional[TracebackType],
    ) -> None:
        self.total_time = time.time() - self._start_time
        __builtins__["__import__"] = self._original_import  # type:ignore

    # def _profiled_import(self, name, globals=None, locals=None, fromlist=(), level=0):
    def _profiled_import(
        self,
        name: str,
        globals: Dict[str, Any] = None,
        locals: Dict[str, Any] = None,
        fromlist: Tuple = (),
        level: int = 0,
    ) -> None:
        # print('Importing {}'.format(repr(name)))
        imp_mod = ImportedModule(
            name=name,
            globals=globals,
            level=level,
            parent=self._import_stack[-1] if self._import_stack else None,
        )
        if not self._import_stack:
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

        for imp_mod in self._top_imp_modules:
            print_imp_mod(imp_mod)
        print()
        print("Total import time: {}ms".format(int(self.total_time * 1000)))
