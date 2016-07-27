# -*- coding: utf-8 -*-
# Copyright (C) 2015-2016 Martin Sandve Alnæs
#
# This file is part of DIJITSO.
#
# DIJITSO is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# DIJITSO is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with DIJITSO. If not, see <http://www.gnu.org/licenses/>.

"""Utilities for interfacing with the system."""

from __future__ import print_function
from __future__ import unicode_literals

import os
import subprocess
import sys
import errno
import gzip
import shutil
import uuid
from glob import glob
from dijitso.log import warning


def make_dirs(path):
    """Creates a directory (tree).

    Ignores error if the directory already exists.
    """
    try:
        os.makedirs(path)
    except os.error as e:
        if e.errno != errno.EEXIST:
            raise


def rename_file(src, dst):
    """Rename a file.

    Ignores error if the destination file exists.
    """
    try:
        os.rename(src, dst)
    except os.error as e:
        # Windows may trigger on existing destination
        if e.errno not in errno.EEXIST:
            raise


def try_rename_file(src, dst):
    """Try to rename a file.

    NB! Ignores error if the SOURCE doesn't exist or the destination already exists.
    """
    try:
        os.rename(src, dst)
    except os.error as e:
        # Windows may trigger on existing destination,
        # everyone triggers on missing source
        if e.errno not in (errno.ENOENT, errno.EEXIST):
            raise


def try_copy_file(src, dst):
    """Try to copy a file.

    NB! Ignores any error.
    """
    try:
        shutil.copy(src, dst)
    except:
        pass


def try_delete_file(filename):
    """Try to remove a file.

    Ignores error if filename doesn't exist.
    """
    try:
        os.remove(filename)
    except os.error as e:
        if e.errno != errno.ENOENT:
            raise


def gzip_file(filename):
    """Gzip a file.

    New file gets .gz extension added.

    Does nothing if the .gz file already exists.

    Original file is never touched.
    """
    # Avoid doing work if file is already there
    gz_filename = filename + ".gz"
    if os.path.exists(filename) and not os.path.exists(gz_filename):
        # Write gzipped contents to a temp file
        tmp_filename = filename + "-tmp-" + uuid.uuid4().hex + ".gz"
        with open(filename, "rb") as f_in, gzip.open(tmp_filename, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)
        # Safe move to target filename, other processes may compete here
        lockfree_move_file(tmp_filename, gz_filename)


def read_file(filename):
    "Try to read file content, if necessary unzipped from filename.gz, return None if not found."
    content = None
    if os.path.exists(filename):
        with open(filename, "r") as f:
            content = f.read()
    elif os.path.exists(filename + ".gz"):
        with gzip.open(filename + ".gz") as f:
            content = f.read()
    return content


def move_file(srcfilename, dstfilename):
    """Move or copy a file."""
    assert os.path.exists(srcfilename)
    shutil.move(srcfilename, dstfilename)
    assert not os.path.exists(srcfilename)
    assert os.path.exists(dstfilename)


def lockfree_move_file(src, dst):
    """Lockfree and portable nfs safe file move operation.

    Taken from textual description at
    http://stackoverflow.com/questions/11614815/a-safe-atomic-file-copy-operation
    """
    if not os.path.exists(src):
        raise RuntimeError("Source file does not exist.")

    if os.path.exists(dst):
        with open(src) as f:
            s = f.read()
        with open(dst) as f:
            d = f.read()
        if s != d:
            warning("Not overwriting existing file with different contents:\nsrc: %s\ndst: %s" % (src, dst))
        else:
            try_delete_file(src)
        return

    def priv(j):
        return dst + ".priv." + str(j)

    def pub(j):
        return dst + ".pub." + str(j)

    # Create a universally unique 128 bit integer id
    ui = uuid.uuid4().int

    # Move or copy file onto the target filesystem
    move_file(src, priv(ui))

    # Atomic rename to make file visible to competing processes
    rename_file(priv(ui), pub(ui))

    # Find uuids of competing files
    n = len(pub("*")) - 1
    uuids = sorted(int(fn[n:]) for fn in glob(pub("*")))

    # Try to delete all files with larger uuids
    for i in uuids:
        if i > ui:
            try_delete_file(pub(i))
    for i in uuids:
        if i < ui:
            # Our file is the one with a larger uuid
            try_delete_file(pub(ui))
            # Cooperate on handling uuid i
            ui = i

    if os.path.exists(dst):
        # If somebody else beat us to it, delete our file
        try_delete_file(pub(ui))
    else:
        # Otherwise do an atomic rename to make our file final
        try_rename_file(pub(ui), dst)
    if os.path.exists(src):
        raise RuntimeError("Source file should not exist at this point!")
    if not os.path.exists(dst):
        raise RuntimeError("Destination file should exist at this point!")


# Copied in from Instant
def get_status_output(cmd, input=None, cwd=None, env=None):
    """Replacement for commands.getstatusoutput which does not work on
Windows (or Python 3)"""
    if isinstance(cmd, str):
        cmd = cmd.strip().split()

    # NOTE: This is not OFED-fork-safe! Check subprocess.py,
    #       http://bugs.python.org/issue1336#msg146685
    #       OFED-fork-safety means that parent should not
    #       touch anything between fork() and exec(),
    #       which is not met in subprocess module. See
    #       https://www.open-mpi.org/faq/?category=openfabrics#ofa-fork
    #       http://www.openfabrics.org/downloads/OFED/release_notes/OFED_3.12_rc1_release_notes#3.03
    pipe = subprocess.Popen(cmd, shell=False, cwd=cwd, env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    (output, errout) = pipe.communicate(input=input)
    assert not errout

    status = pipe.returncode
    output = output.decode('utf-8') if sys.version_info[0] > 2 else output

    return (status, output)
