# -*- coding: utf-8 -*-
# Copyright (C) 2015-2015 Martin Sandve Alnæs
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
import os, errno, ctypes, gzip, shutil, uuid
from glob import glob

def makedirs(path):
    """Creates a directory (tree). If directory already exists it does nothing."""
    try:
        os.makedirs(path)
    except os.error as e:
        if e.errno != errno.EEXIST:
            raise

def deletefile(filename):
    """Remove a file. If the file is not there it does nothing."""
    try:
        os.remove(filename)
    except os.error as e:
        if e.errno != errno.ENOENT:
            raise

# TODO: Copy here to make configurable through dijitso params.
#       Just letting it stay in instant for now.
from instant import get_status_output
