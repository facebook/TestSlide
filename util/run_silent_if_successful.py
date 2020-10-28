#!/usr/bin/env python3

# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import os
import pty
import signal
import subprocess
import sys
import threading

master_pty_fd, slave_pty_fd = pty.openpty()
read_data = []


def master_pty_fd_reader():
    while True:
        try:
            data = os.read(master_pty_fd, 1024)
        except OSError:
            return
        else:
            if data:
                read_data.append(data)
            else:
                return


master_pty_fd_reader_thread = threading.Thread(target=master_pty_fd_reader)

master_pty_fd_reader_thread.start()

pid = None


def handler(signal_number, frame):
    if not pid:
        return
    os.kill(pid, signal_number)


signal.signal(signal.SIGINT, handler)
signal.signal(signal.SIGTERM, handler)
signal.signal(signal.SIGHUP, handler)

try:
    popen = subprocess.Popen(
        sys.argv[1:],
        stdin=subprocess.DEVNULL,
        stdout=slave_pty_fd,
        stderr=slave_pty_fd,
    )
except FileNotFoundError as e:
    print(str(e), file=sys.stderr)
    os.close(slave_pty_fd)
    master_pty_fd_reader_thread.join()
    sys.exit(127)

pid = popen.pid

returncode = popen.wait()

os.close(slave_pty_fd)

master_pty_fd_reader_thread.join()

if returncode:
    for data in read_data:
        os.write(sys.stdout.fileno(), data)
    sys.exit(returncode)
