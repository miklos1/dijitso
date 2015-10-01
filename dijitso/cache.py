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

"""Utilities for disk cache features of dijitso."""

from __future__ import print_function
import os
import ctypes
import gzip

def create_src_filename(signature, cache_params):
    "Create source code filename based on signature and params."
    basename = cache_params["src_prefix"] + signature + cache_params["src_postfix"]
    return os.path.join(cache_params["src_dir"], basename)

def create_lib_filename(signature, cache_params):
    "Create library filename based on signature and params."
    basename = cache_params["lib_prefix"] + signature + cache_params["lib_postfix"]
    return os.path.join(cache_params["lib_dir"], basename)

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

_lib_cache = {}
def lookup_lib(signature, cache_params):
    """Lookup library in memory cache then in disk cache.

    Returns library module if found, otherwise None.
    """
    # Look for already loaded library in memory cache
    lib = _lib_cache.get(signature)
    if lib is None:
        # Cache miss in memory, try looking on disk
        lib = load_library(signature, cache_params)
    # Return library or None
    return lib

def store_src(signature, src, cache_params):
    "Store source code in file within dijitso directories."
    makedirs(cache_params["src_dir"])
    src_filename = create_src_filename(signature, cache_params)

    if not os.path.exists(src_filename):
        # Expected behaviour: just write the code to file
        with open(src_filename, "w") as f:
            f.write(src)
    else:
        # Error handling if the file was already there
        with open(src_filename, "r") as f:
            found_src = f.read()
        if found_src != src:
            # If the existing source code file has different content, fail
            # after writing new and different source to file with .newer suffix
            with open(src_filename + ".new", "w") as f:
                f.write(src)
            error("File\n  %s\nalready exists and its contents are different.\n"
                  "The new source code has been written to\n  %s" % (src_filename, src_filename+".new"))
    return src_filename

def compress_source_code(src_filename, cache_params):
    # Keep, delete or compress source code
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
