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
import errno
import ctypes
import gzip
import shutil
import os
import uuid
from glob import glob


# TODO: If we need file locking, add support here and make
# sure all filesystem access in dijitso pass through here
# by searching for use of 'os', 'sys', 'shutil'.
#from flufl.lock import Lock
#l = Lock(dst)


def make_dirs(path):
    """Creates a directory (tree). If directory already exists it does nothing."""
    try:
        os.makedirs(path)
    except os.error as e:
        if e.errno != errno.EEXIST:
            raise


def rename_file(src, dst):
    """Rename a file. If the destination file exists, it does nothing."""
    try:
        os.rename(src, dst)
    except os.error as e:
        # Windows may trigger on existing destination
        if e.errno not in errno.EEXIST:
            raise


def try_rename_file(src, dst):
    """Try to rename a file. If either the source file doesn't exist or the destination file exists, it does nothing."""
    try:
        print("Trying rename:", src, dst)
        os.rename(src, dst)
    except os.error as e:
        # Windows may trigger on existing destination,
        # everyone triggers on missing source
        if e.errno not in (errno.ENOENT, errno.EEXIST):
            raise


def delete_file(filename):
    """Remove a file. If the file is not there it does nothing."""
    try:
        os.remove(filename)
    except os.error as e:
        if e.errno != errno.ENOENT:
            raise


def gzip_file(filename):
    """Gzip a file, new file gets .gz extension, old file is removed."""
    with open(filename, "rb") as f_in, gzip.open(filename + ".gz", "wb") as f_out:
        shutil.copyfileobj(f_in, f_out)
        delete_file(filename)


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
            raise RuntimeError("Destination file already exists but contents differ!\nsrc: %s\ndst: %s" % (src, dst))
        else:
            delete_file(src)
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
            delete_file(dst + ".pub." + str(i))
    for i in uuids:
        if i < ui:
            # Our file is the one with a larger uuid
            delete_file(dst + ".pub." + str(ui))
            # Cooperate on handling uuid i
            ui = i

    # If somebody else beat us to it, delete our file
    if os.path.exists(dst):
        delete_file(dst + ".pub." + str(ui))
    else:
        # Atomic rename to make file final
        try_rename_file(pub(ui), dst)
    if os.path.exists(src):
        raise RuntimeError("Source file should not exist at this point!")
    if not os.path.exists(dst):
        raise RuntimeError("Destination file should exist at this point!")


# TODO: Copy here to make configurable through dijitso params.
#       Just letting it stay in instant for now.
from instant import get_status_output
