# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.


import sys
import unittest  # noqa

import testslide.bdd.dsl as dsl
import testslide.core.lib as lib
import testslide.core.matchers as matchers
import testslide.core.mock_callable as mock_callable
import testslide.core.mock_constructor as mock_constructor
import testslide.core.patch_attribute as patch_attribute
import testslide.core.strict_mock as strict_mock  # noqa
import testslide.executor.cli as cli
import testslide.executor.import_profiler as import_profiler
import testslide.executor.runner as runner
from testslide.bdd.lib import _ContextData, Context  # noqa
from testslide.core import _importer, TestCase  # noqa
from testslide.core.strict_mock import StrictMock  # noqa

# I'm sorry. I know. This is necessary to provide backwards compatibility with TestSlide 2.0 so I don't break the world.
sys.modules["testslide.lib"] = lib
sys.modules["testslide.matchers"] = matchers
sys.modules["testslide.mock_callable"] = mock_callable
sys.modules["testslide.mock_constructor"] = mock_constructor
sys.modules["testslide.patch_attribute"] = patch_attribute
sys.modules["testslide.strict_mock"] = strict_mock
sys.modules["testslide.dsl"] = dsl
sys.modules["testslide.cli"] = cli
sys.modules["testslide.import_profiler"] = import_profiler
sys.modules["testslide.runner"] = runner
