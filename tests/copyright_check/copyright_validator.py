# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import print_function

import difflib

import os
import re
import sys
import pathlib
import config

print_logs = config.print_logs


def fetch_samplefile():
    """
    Method to fetch sample copyright file
    :return sample
    """
    sample = dict()
    path = os.path.join(config.default_check_dir, config.default_sample_file)
    ext = pathlib.Path(config.default_sample_file).suffix.split(".")[1]
    sample_file = open(path, "r")
    ref = sample_file.read().splitlines()
    sample_file.close()
    sample[ext] = ref

    return sample


def verify_file(filename, sample, formula):
    """
    Method to check if file meets copyright signature expectations
    :param filename file to check
    :param sample copyright signature file
    :param formula regex to verify
    :return bool
    """
    try:
        f = open(filename, "r")
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
        p = formula.get("py_files")
        (data, _) = p.subn("", data, 1)

    data = data.splitlines()

    # if our test file is smaller than the reference it surely fails!
    if len(demo) > len(data):
        print(
            "File %s smaller than sample file(%d < %d)"
            % (filename, len(data), len(demo)),
            file=print_logs,
        )
        return False

    # trim our file to the same number of lines as the reference file
    data = data[: len(demo)]

    if demo != data:
        print(
            "Header in %s does not match sample file, diff:" % filename, file=print_logs
        )
        if print_logs:
            for line in difflib.unified_diff(
                demo, data, "sample", filename, lineterm=""
            ):
                print(line, file=print_logs)
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

    allfiles = list()

    if len(config.filelist) > 0:
        allfiles = config.filelist
    else:
        for root, dirs, traverse in os.walk(config.rootdir):
            for d in config.ignore_dirs:
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
    formula["py_files"] = re.compile(r"^(#!.*\n)\n*", re.MULTILINE)
    sample = fetch_samplefile()
    filelists = fetch_files(sample.keys())
    failure_list = list()
    for filename in filelists:
        if not verify_file(filename, sample, formula):
            failure_list.append(os.path.relpath(filename))
            print(
                "Copyright structure missing or incorrect for: ",
                os.path.relpath(filename),
            )
    if len(failure_list) > 0:
        return 1
    return


if __name__ == "__main__":
    sys.exit(main())
