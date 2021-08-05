# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.


import sys
import os


debug_logs = False
print_logs = sys.stderr if debug_logs else open("/dev/null", "w")

validator_path = "tests/copyright_check"
default_sample_file = "copyright_signature.py"

rootdir = os.path.abspath(os.path.dirname(__file__) + "/../../")
default_check_dir = os.path.join(rootdir, validator_path)

# if want to run specific files, add to this list
filelist = list()
