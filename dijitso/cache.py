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

"""Utilities for disk cache features of dijitso."""

from __future__ import unicode_literals

import uuid
import os
import ctypes
from dijitso.system import make_dirs, try_delete_file, gzip_file, read_file, lockfree_move_file
from dijitso.log import log, warning, error


def create_log_filename(signature, cache_params):
    "Create log filename based on signature and params."
    basename = signature + cache_params["log_postfix"]
    return os.path.join(cache_params["cache_dir"], cache_params["log_dir"], basename)

def create_inc_filename(signature, cache_params):
    "Create header filename based on signature and params."
    basename = signature + cache_params["inc_postfix"]
    return os.path.join(cache_params["cache_dir"], cache_params["inc_dir"], basename)

def create_src_filename(signature, cache_params):
    "Create source code filename based on signature and params."
    basename = signature + cache_params["src_postfix"]
    return os.path.join(cache_params["cache_dir"], cache_params["src_dir"], basename)

def create_lib_basename(signature, cache_params):
    "Create library filename based on signature and params."
    basename = cache_params["lib_prefix"] + signature + cache_params["lib_postfix"]
    return basename

def create_lib_filename(signature, cache_params):
    "Create library filename based on signature and params."
    basename = create_lib_basename(signature, cache_params)
    return os.path.join(cache_params["cache_dir"], cache_params["lib_dir"], basename)


def make_inc_dir(cache_params):
    d = os.path.join(cache_params["cache_dir"], cache_params["inc_dir"])
    make_dirs(d)
    return d

def make_src_dir(cache_params):
    d = os.path.join(cache_params["cache_dir"], cache_params["src_dir"])
    make_dirs(d)
    return d

def make_lib_dir(cache_params):
    d = os.path.join(cache_params["cache_dir"], cache_params["lib_dir"])
    make_dirs(d)
    return d

def make_log_dir(cache_params):
    d = os.path.join(cache_params["cache_dir"], cache_params["log_dir"])
    make_dirs(d)
    return d

_ensure_dirs_called = False
def ensure_dirs(cache_params):
    global _ensure_dirs_called
    if not _ensure_dirs_called:
        make_inc_dir(cache_params)
        make_src_dir(cache_params)
        make_lib_dir(cache_params)
        make_log_dir(cache_params)
        _ensure_dirs_called = True


def read_library_binary(lib_filename):
    "Read compiled shared library as binary blob into a numpy byte array."
    import numpy
    return numpy.fromfile(lib_filename, dtype=numpy.uint8)

def write_library_binary(lib_data, signature, cache_params):
    "Store compiled shared library from binary blob in numpy byte array to cache."
    make_lib_dir(cache_params)
    lib_filename = create_lib_filename(signature, cache_params)
    lib_data.tofile(lib_filename)
    # TODO: Set permissions?


def load_library(signature, cache_params):
    """Load existing dynamic library from disk.

    Returns library module if found, otherwise None.

    If found, the module is placed in memory cache for later lookup_lib calls.
    """
    lib_filename = create_lib_filename(signature, cache_params)
    if not os.path.exists(lib_filename):
        return None
    try:
        lib = ctypes.cdll.LoadLibrary(lib_filename)
    except os.error as e:
        error("Failed to load library %s." % (lib_filename,))

    if lib is not None:
        # Disk loading succeeded, register loaded library in memory cache for next time
        _lib_cache[signature] = lib
    return lib


# A cache is always something to be careful about.
# This one stores references to loaded jit-compiled libraries,
# which will stay in memory unless manually unloaded anyway
# and should not cause any trouble.
_lib_cache = {}
def lookup_lib(lib_signature, cache_params):
    """Lookup library in memory cache then in disk cache.

    Returns library module if found, otherwise None.
    """
    # Look for already loaded library in memory cache
    lib = _lib_cache.get(lib_signature)
    if lib is None:
        # Cache miss in memory, try looking on disk
        lib = load_library(lib_signature, cache_params)
    # Return library or None
    return lib


def read_src(signature, cache_params):
    """Lookup source code in disk cache and return file contents or None."""
    filename = create_src_filename(signature, cache_params)
    return read_file(filename)

def read_inc(signature, cache_params):
    """Lookup header file in disk cache and return file contents or None."""
    filename = create_inc_filename(signature, cache_params)
    return read_file(filename)

def read_log(signature, cache_params):
    """Lookup log file in disk cache and return file contents or None."""
    filename = create_log_filename(signature, cache_params)
    return read_file(filename)


def store_textfile(filename, content):
    # Generate a unique temporary filename in same directory as the target file
    ui = uuid.uuid4().hex
    tmp_filename = filename + "." + str(ui)

    # Write the text to a temporary file
    with open(tmp_filename, "w") as f:
        f.write(content)

    # Safely move file to target filename
    lockfree_move_file(tmp_filename, filename)

    return filename

def store_src(signature, content, cache_params):
    "Store source code in file within dijitso directories."
    make_src_dir(cache_params)
    filename = create_src_filename(signature, cache_params)
    store_textfile(filename, content)
    return filename

def store_inc(signature, content, cache_params):
    "Store header file within dijitso directories."
    make_inc_dir(cache_params)
    filename = create_inc_filename(signature, cache_params)
    store_textfile(filename, content)
    return filename

def store_log(signature, content, cache_params):
    "Store log file within dijitso directories."
    make_log_dir(cache_params)
    filename = create_log_filename(signature, cache_params)
    store_textfile(filename, content)
    return filename


def compress_source_code(src_filename, cache_params):
    """Keep, delete or compress source code based on value of cache parameter 'src_storage'.

    Can be "keep", "delete", or "compress".
    """
    src_storage = cache_params["src_storage"]
    if src_storage == "keep":
        pass
    elif src_storage == "delete":
        try_delete_file(src_filename)
    elif src_storage == "compress":
        gzip_file(src_filename)
        try_delete_file(src_filename)
    else:
        error("Invalid src_storage parameter. Expecting 'keep', 'delete', or 'compress'.")
