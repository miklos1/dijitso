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

import os
import ctypes
import gzip
import shutil
from dijitso.system import makedirs, deletefile
from dijitso.log import log, error


def create_inc_filename(signature, cache_params):
    "Create source code filename based on signature and params."
    basename = signature + cache_params["inc_postfix"]
    return os.path.join(cache_params["root_dir"], cache_params["inc_dir"], basename)

def create_src_filename(signature, cache_params):
    "Create source code filename based on signature and params."
    basename = signature + cache_params["src_postfix"]
    return os.path.join(cache_params["root_dir"], cache_params["src_dir"], basename)

def create_lib_filename(signature, cache_params):
    "Create library filename based on signature and params."
    basename = cache_params["lib_prefix"] + signature + cache_params["lib_postfix"]
    return os.path.join(cache_params["root_dir"], cache_params["lib_dir"], basename)


def make_inc_dir(cache_params):
    makedirs(os.path.join(cache_params["root_dir"], cache_params["inc_dir"]))

def make_src_dir(cache_params):
    makedirs(os.path.join(cache_params["root_dir"], cache_params["src_dir"]))

def make_lib_dir(cache_params):
    makedirs(os.path.join(cache_params["root_dir"], cache_params["lib_dir"]))

def make_log_dir(cache_params):
    makedirs(os.path.join(cache_params["root_dir"], cache_params["log_dir"]))

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
    if os.path.exists(filename):
        # Error handling if the file was already there
        with open(filename, "r") as f:
            old_content = f.read()
        if old_content != content:
            # If the existing source code file has different content, make a backup and warn again.
            # after writing new and different source to file with .newer suffix
            with open(filename + ".orig", "w") as f:
                f.write(old_content)
            # Now write the code to file, overwriting previous content
            with open(filename, "w") as f:
                f.write(content)
            warning("The old file contents differ from the new and has been backed up as:\n  %s" % (filename+".orig",))
        else:
            warning("File already exists with same contents in dijitso cache:\n  %s" % (filename,))
    else:
        # Write the code to new file
        with open(filename, "w") as f:
            f.write(content)
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


def compress_source_code(src_filename, cache_params):
    """Keep, delete or compress source code based on value of cache parameter 'src_storage'.

    Can be "keep", "delete", or "compress".
    """
    src_storage = cache_params["src_storage"]
    if src_storage == "keep":
        pass
    elif src_storage == "delete":
        deletefile(src_filename)
    elif src_storage == "compress":
        with open(src_filename, "rb") as f_in, gzip.open(src_filename + ".gz", "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)
        deletefile(src_filename)
    else:
        error("Invalid src_storage parameter. Expecting 'keep', 'delete', or 'compress'.")
