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

from __future__ import print_function
import os, errno, ctypes, shutil, uuid
from glob import glob
import numpy

from dijitso.system import makedirs, deletefile
from dijitso.log import log, error
from dijitso.params import validate_params
from dijitso.cache import lookup_lib, load_library
from dijitso.cache import write_library_binary, read_library_binary
from dijitso.cache import lookup_src, store_src, compress_source_code
from dijitso.build import build_shared_library

import hashlib

def extend_signature(sig, params):
    "Extend a signature hash with a parameter hash."
    h = hashlib.sha1()
    for k in sorted(params):
        h.update(repr((k, params[k])))
    return sig[:8] + "_" + h.hexdigest()[:8]

def extract_factory_function(lib, name):
    """Extract function from loaded library.

    Assuming signature "(void *)()", for anything else use look at ctypes documentation.

    Returns the factory function or raises error.
    """
    function = getattr(lib, name)
    function.restype = ctypes.c_void_p
    return function

def jit(signature, jitable, params, generate=None, send=None, receive=None, wait=None):
    """Driver for just in time compilation and import of a shared library with a cache mechanism.

    The signature is used to identity if the library
    has already been compiled and cached. A two-level
    memory and disk cache ensures good performance
    for repeated lookups within a single program as
    well as persistence across program runs.

    If no library has been cached, the passed 'generate'
    function is called with the arguments:

        src = generate(signature, jitable, build_params)

    It is expected to translate the 'jitable' object into
    C or C++(default) source code which will subsequently be
    compiled as a shared library and stored in the disk cache.

    The compiled shared library is then loaded with ctypes and returned.

    For use in a parallel (MPI) context, three functions send, receive,
    and wait can be provided. Each process can take on a different role
    depending on whether generate, or receive, or neither is provided.

      * Every process that gets a generate function is called a 'builder',
        and will generate and compile code as described above on a cache miss.
        If the function send is provided, it will then send the shared library
        binary file as a binary blob by calling send(numpy_array).

      * Every process that gets a receive function is called a 'receiver',
        and will call 'numpy_array = receive()' expecting the binary blob
        with a compiled binary shared library which will subsequently be
        written to file in the local disk cache.

      * The rest of the processes are called 'waiters' and will do nothing.

      * If provided, all processes will call wait() before attempting to
        load the freshly compiled library from disk cache.

    The intention of the above pattern is to be flexible, allowing several
    different strategies for sharing build results. The user of dijitso
    can determine groups of processes that share a disk cache, and assign
    one process per physical disk cache directory to write to that directory,
    avoiding multiple processes writing to the same files.

    This forms the basis for three main strategies:

      * Build on every process.

      * Build on one process per physical cache directory.

      * Build on a single global root node and send a copy of
        the binary to one process per physical cache directory.

    It is not recommended to have multiple builder processes sharing
    a physical cache directory.
    """
    params = validate_params(params)

    # Combine jitable signature and parameters
    #src_signature = extend_signature(signature, params["generator_params"])
    #lib_signature = extend_signature(src_signature, params["build_params"])
    # FIXME: Improve signature handling
    src_signature = signature
    lib_signature = signature

    # Look for library in memory or disk cache
    cache_params = params["cache_params"]
    lib = lookup_lib(lib_signature, cache_params)

    if lib is None:
        # Since we didn't find the library in cache, we must build it.

        if generate is not None:
            if receive is not None:
                error("Please provide only one of generate or receive.")

            # Look for source code in cache before eventually generating the code
            src_filename = lookup_src(src_signature, cache_params)

            if src_filename is None:
                # 1) Generate source code
                src = generate(src_signature, jitable, params["generator_params"])
                # TODO: Get header and implementation content separately

                # 2) Store source code in dijitso src dir
                src_filename = store_src(src_signature, src, params["cache_params"])
                # TODO: Store header and implementation separately

            # 3) Compile shared library and store in cache
            lib_filename = build_shared_library(lib_signature, src_filename, params)

            # Locally compress or delete source code based on params
            compress_source_code(src_filename, cache_params)

            # 4) Send library over network if we have a send function
            if send is not None:
                lib_data = read_library_binary(lib_filename)
                send(lib_data)

        elif receive is not None:
            # 4) Get library as binary blob from given receive function and store in cache
            lib_data = receive()
            write_library_binary(lib_data, lib_signature, cache_params)

        else:
            # Do nothing
            pass

        # 5) Notify waiters that we're done / wait for builder to notify us
        if wait is not None:
            wait()

        # Finally load library from disk cache (places in memory cache)
        lib = load_library(lib_signature, cache_params)

    # Return library
    return lib
