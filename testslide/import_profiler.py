#!/usr/bin/env python3
# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import inspect
import sys
import time


class ImportedModule(object):
    """
    A module that was imported with __import__.
    """

    def __init__(self, name, globals, level, filename, lineno, parent=None):
        self.name = name
        self.globals = globals
        self.level = level
        self.filename = filename
        self.lineno = lineno
        self.parent = parent
        self.children = []
        self.time = None
        if parent:
            parent.children.append(self)

    def __eq__(self, value):
        return str(self) == str(value)

    @property
    def all_children(self):
        children = []

        for child in self.children:
            children.append(child)
            children.extend(child.all_children)

        return children

    @property
    def own_time(self):
        """
        How many seconds it took to import this module, minus all child imports.
        """
        return self.time - sum(child.time for child in self.children)

    def __str__(self):
        if self.globals and self.level:
            if self.level == 1:
                prefix = self.globals["__package__"]
            else:
                end = -1 * (self.level - 1)
                prefix = ".".join(self.globals["__package__"].split(".")[:end]) + "."
        else:
            prefix = ""
        return "{}{}".format(prefix, self.name)

    def __enter__(self):
        self._start_time = time.time()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.time = time.time() - self._start_time


class ImportProfiler(object):
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

    def __init__(self):
        self._original_import = __builtins__["__import__"]

    def __enter__(self):
        __builtins__["__import__"] = self._profiled_import
        self._top_imp_modules = []
        self._import_stack = []
        self.total_time = None
        self._start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.total_time = time.time() - self._start_time
        __builtins__["__import__"] = self._original_import

    def _profiled_import(self, name, globals=None, locals=None, fromlist=(), level=0):
        if sys.version_info.major >= 3 and sys.version_info.minor >= 6:
            frameinfo = inspect.getframeinfo(inspect.stack()[1][0])
            filename = frameinfo.filename
            lineno = frameinfo.lineno
        else:
            frame = inspect.stack()[1][0]
            filename = inspect.getsourcefile(frame) or inspect.getfile(frame)
            lineno = inspect.getframeinfo(frame).lineno

        imp_mod = ImportedModule(
            name=name,
            globals=globals,
            level=level,
            filename=filename,
            lineno=lineno,
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

    def print_stats(self, threshold_ms=0, trim_path_prefix=None):
        def print_imp_mod(imp_mod, indent=0):
            own_ms = int(imp_mod.own_time * 1000)
            if own_ms >= threshold_ms or any(
                child
                for child in imp_mod.all_children
                if child.own_time * 1000 >= threshold_ms
            ):
                path = imp_mod.filename
                if trim_path_prefix:
                    split = path.split(trim_path_prefix)
                    if len(split) == 2 and not split[0]:
                        path = split[1]
                print(
                    "{}{}: {}ms ({}:{})".format(
                        "  " * indent, imp_mod, own_ms, path, imp_mod.lineno
                    )
                )
            for child_imp_mod in imp_mod.children:
                print_imp_mod(child_imp_mod, indent + 1)

        for imp_mod in self._top_imp_modules:
            print_imp_mod(imp_mod)
        print()
        print("Total import time: {}ms".format(int(self.total_time * 1000)))
