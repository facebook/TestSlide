# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import sys
import inspect

if sys.version_info[0] >= 3:
    from unittest.mock import create_autospec
else:
    from mock import create_autospec


def _add_signature_validation(value, template, attr_name):
    template_function = getattr(template, attr_name)
    if sys.version_info[0] == 2 and not (
        not inspect.isfunction(template_function) and not template_function.im_self
    ):
        # This is needed for Python 2, as create_autospec breaks
        # with TypeError when caling either static or class
        # methods
        return create_autospec(template_function, side_effect=value)
    else:
        instance_mock = create_autospec(template)
        function_mock = getattr(instance_mock, attr_name)
        function_mock.side_effect = value
        return function_mock
