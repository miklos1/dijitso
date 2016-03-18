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

import os, errno, ctypes, gzip, shutil, uuid
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
    """Move or copy a file. If the file is not there it does nothing."""
    shutil.move(srcfilename, dstfilename)


# TODO: Copy here to make configurable through dijitso params.
#       Just letting it stay in instant for now.
from instant import get_status_output
