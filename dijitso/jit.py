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
from dijitso.mpi import create_comms_and_role, send_library, receive_library
from dijitso.cache import create_lib_filename, load_library, lookup_lib, store_src, compress_source_code
from dijitso.build import build_shared_library

def extract_factory_function(lib, name):
    """Extract function from loaded library.

    Assuming signature "(void *)()", for anything else use look at ctypes documentation.

    Returns the factory function or raises error.
    """
    function = getattr(lib, name)
    function.restype = ctypes.c_void_p
    return function

def jit(signature, generator, jitable, params, role="builder", copy_comm=None, wait_comm=None):
    """Driver for just in time compilation and import of a shared library with a cache mechanism.

    The signature is used to identity if the library
    has already been compiled and cached. A two-level
    memory and disk cache ensures good performance
    for repeated lookups within a single program as
    well as persistence across program runs.

    If no library has been cached, the passed 'generator'
    function is called with the arguments:

        src = generator(signature, jitable, build_params)

    It is expected to translate the 'jitable' object into
    C or C++(default) source code which will subsequently be
    compiled as a shared library and stored in the disk cache.

    The compiled shared library is then loaded with ctypes and returned.
    """
    params = validate_params(params)

    # Look for library in memory or disk cache
    cache_params = params["cache_params"]
    lib = lookup_lib(signature, cache_params)

    if lib is None:
        # Since we didn't find the library in cache, we must build it.

        # TODO: Should call these once (for each comm at least) globally in dolfin, not on each jit call
        #comm_dir = os.path.join(cache_params["root_dir"], cache_params["comm_dir"])
        #copy_comm, wait_comm, role = create_comms_and_role(comm, comm_dir, buildon)

        if role == "builder":
            # 1) Generate source code
            src = generator(signature, jitable, params["generator_params"])

            # 2) Store source code in dijitso src dir
            src_filename = store_src(signature, src, params["cache_params"])

            # 3) Compile shared library and store in cache
            lib_filename = build_shared_library(signature, src_filename, params)

            # 4) Send library over network if we have a copy_comm
            if copy_comm is not None and copy_comm.size > 1:
                send_library(copy_comm, lib_filename, params)

            # Locally compress or delete source code based on params
            compress_source_code(src_filename, cache_params)

        elif role == "receiver":
            # 4) Get library as binary blob over MPI and store in cache
            assert copy_comm is not None
            receive_library(copy_comm, signature, cache_params)

        elif role == "waiter":
            # Do nothing
            pass

        else:
            error("Invalid role %s" % (role,))

        # 5) Notify waiting processes that we're done
        if wait_comm is not None:
            wait_comm.Barrier()

        # Finally load library from disk cache (places in memory cache)
        lib = load_library(signature, cache_params)

    # Return library
    return lib
