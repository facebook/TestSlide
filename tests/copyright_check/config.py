# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from pathlib import Path
from typing import List

debug_logs = False

default_sample_file = "copyright_signature.py"
rootdir = Path(__file__).parent.parent.absolute()
default_check_dir = rootdir / "copyright_check"

# if want to run specific files, add to this list
filelist: List[str] = []

# If we want to ignore, add directories in ignore_dirs
ignore_dirs: List[str] = []
