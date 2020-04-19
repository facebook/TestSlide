#!/usr/bin/env python

import os
import pty
import signal
import subprocess
import sys
import threading


master_pty_fd, slave_pty_fd = pty.openpty()
read_data = []
returncode = None


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

popen = subprocess.Popen(
    sys.argv[1:], stdin=subprocess.DEVNULL, stdout=slave_pty_fd, stderr=slave_pty_fd,
)

returncode = popen.wait()

os.close(slave_pty_fd)

master_pty_fd_reader_thread.join()

if returncode:
    for data in read_data:
        os.write(sys.stdout.fileno(), data)
    sys.exit(returncode)
