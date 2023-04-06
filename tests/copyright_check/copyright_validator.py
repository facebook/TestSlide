#!/usr/bin/env python

# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import print_function

import difflib
import os
import pathlib
import re
import sys

import config  # type: ignore[import]


def print_logs(*args, **kwargs):
    if not config.debug_logs:
        return
    print(*args, **kwargs)


def fetch_samplefile():
    """
    Method to fetch sample copyright file
    :return sample
    """
    path = config.default_check_dir / config.default_sample_file
    ext = pathlib.Path(config.default_sample_file).suffix.split(".")[1]
    with path.open() as f:
        ref = f.read().splitlines()

    return {ext: ref}


def verify_file(filename, sample, formula):
    """
    Method to check if file meets copyright signature expectations
    :param filename file to check
    :param sample copyright signature file
    :param formula regex to verify
    :return bool
    """
    try:
        with open(filename, "r") as f:
            data = f.read()
    except Exception as exc:
        print_logs("Unable to open {0}: {1}".format(filename, exc))
        return False

    basename = os.path.basename(filename)
    ext = get_extension(filename)

    demo = sample[ext] if ext != "" else sample[basename]
    if ext == "py":
        p = formula.get("py_files")
        (data, _) = p.subn("", data, 1)

    data = data.splitlines()

    # if our test file is smaller than the reference it surely fails!
    if len(demo) > len(data):
        print_logs(
            "File {0} smaller than sample file({1} < {2})".format(
                filename, len(data), len(demo)
            )
        )
        return False

    # trim our file to the same number of lines as the reference file
    data = data[: len(demo)]

    if demo != data:
        print_logs("Header in {} does not match sample file, diff:".format(filename))
        if config.debug_logs:
            for line in difflib.unified_diff(
                demo, data, "sample", filename, lineterm=""
            ):
                print_logs(line)
        return False

    return True


def get_extension(filename):
    """
    Method to get extension of file
    """
    return os.path.splitext(filename)[1].split(".")[-1].lower()


def fetch_files(extensions):
    """
    Method to traverse through repo for files
    :param extensions
    :return outfiles
    """

    allfiles = []

    if config.filelist:
        allfiles = config.filelist
    else:
        for root, dirs, traverse in os.walk(config.rootdir.as_posix()):
            for d in config.ignore_dirs:
                if d in dirs:
                    dirs.remove(d)

            for fname in traverse:
                fpath = os.path.join(root, fname)
                allfiles.append(fpath)

    outfiles = []
    for fpath in allfiles:
        ext = get_extension(fpath)
        if ext in extensions:
            outfiles.append(fpath)
    return outfiles


def main():
    formula = {"py_files": re.compile(r"^(#!.*\n)\n*", re.MULTILINE)}
    sample = fetch_samplefile()
    filelists = fetch_files(sample.keys())
    failure_list = []
    for filename in filelists:
        if not verify_file(filename, sample, formula):
            failure_list.append(os.path.relpath(filename))
            print(
                "Copyright structure missing or incorrect for: ",
                os.path.relpath(filename),
            )
    if failure_list:
        return 1

    print("Copyright structure intact for all python files ")
    return


if __name__ == "__main__":
    sys.exit(main())
