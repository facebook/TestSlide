#!/usr/bin/env python

# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import print_function

import argparse
import difflib
import glob
import os
import re
import sys
import pathlib

parser = argparse.ArgumentParser()
parser.add_argument(
    "filelist",
    help="list of files to check, all files by default",
    nargs='*')

rootdir = os.path.dirname(__file__) + "/../../"
rootdir = os.path.abspath(rootdir)
parser.add_argument(
    "--rootdir", default=rootdir, help="root directory to verify")

validator_path="tests/copyright_check"
default_sample_file="copyright_signature.py"
debug_logs=False

default_check_dir = os.path.join(rootdir, validator_path)

args = parser.parse_args()

print_logs = sys.stderr if debug_logs else open("/dev/null", "w")

def fetch_samplefile():
    sample = dict()
    path=os.path.join(default_check_dir, default_sample_file)
    ext=pathlib.Path(default_sample_file).suffix.split('.')[1]
    sample_file = open(path, 'r')
    ref = sample_file.read().splitlines()
    sample_file.close()
    sample[ext] = ref

    return sample


def verify_file(filename, sample, formula):
    try:
        f = open(filename, 'r')
    except Exception as exc:
        print("Unable to open %s: %s" % (filename, exc), file=print_logs)
        return False

    data = f.read()
    f.close()

    basename = os.path.basename(filename)
    ext = get_extension(filename)

    if ext != "":
        demo = sample[ext]
    else:
        demo = sample[basename]

    if ext == "py":
        p = formula["#!"]
        (data, _) = p.subn("", data, 1)

    data = data.splitlines()

    # if our test file is smaller than the reference it surely fails!
    if len(demo) > len(data):
        print('File %s smaller than sample file(%d < %d)' %
              (filename, len(data), len(demo)),
              file=print_logs)
        return False

    # trim our file to the same number of lines as the reference file
    data = data[:len(demo)]

    if demo != data:
        print("Header in %s does not match sample file, diff:" %
              filename, file=print_logs)
        if print_logs:
            for line in difflib.unified_diff(demo, data, 'sample', filename, lineterm=''):
                print(line, file=print_logs)
        return False

    return True


def get_extension(filename):
    return os.path.splitext(filename)[1].split(".")[-1].lower()

def fetch_files(extensions):
    # If we want to ignore, add directories in ignore_dirs 
    ignore_dirs = list()
    allfiles = list()

    if len(args.filelist) > 0:
        allfiles = args.filelist
    else:
        for root, dirs, traverse in os.walk(args.rootdir):
            for d in ignore_dirs:
                if d in dirs:
                    dirs.remove(d)

            for fname in traverse:
                fpath = os.path.join(root, fname)
                allfiles.append(fpath)

    outfiles = list()
    for fpath in allfiles:
        ext = get_extension(fpath)
        basename = os.path.basename(fpath)
        if ext in extensions or basename in extensions:
            outfiles.append(fpath)
    return outfiles

def main():
    formula = dict()
    formula["#!"] = re.compile(r"^(#!.*\n)\n*", re.MULTILINE)
    sample = fetch_samplefile()
    filelists = fetch_files(sample.keys())
    for filename in filelists:
        if not verify_file(filename, sample, formula):
            print(filename, file=sys.stdout)

    return 0


if __name__ == "__main__":
    sys.exit(main())

