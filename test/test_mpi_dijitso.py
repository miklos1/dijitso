#!/usr/bin/env py.test
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
import pytest
import shutil

#@pytest.fixture(params=["node"])
@pytest.fixture(params=["root", "node", "process"])
def buildon(request):
    return request.param

def test_mpi_jit_strategies(comm, jit_integer, buildon):
    """Jit a simple code generated by inserting a simple integer.

    Covers (if the cache is initially empty):

        - memory cache miss
        - memory cache hit
        - compiling
        - loading
        - factory function extraction

    """
    # Note: this test was initially copied from test_core_jit_framework in test_dijitso.py
    print(buildon, comm.rank)

    if buildon == "process":
        # One dir per process
        dijitso_root_dir = ".test_dijitso_%d" % (comm.rank,)
    elif buildon == "node":
        # Less dirs than processes (gives some waiting for size > 2)
        dijitso_root_dir = ".test_dijitso_%d" % (comm.rank % 2,)
    elif buildon == "root":
        # Less dirs than processes (gives a combination of copying (size>1) and waiting (size>2))
        dijitso_root_dir = ".test_dijitso_%d" % (comm.rank % 2,)

    shutil.rmtree(dijitso_root_dir, ignore_errors=True)
    comm.barrier()

    # This magic value is defined in testincludes/testinclude.h,
    # so this is used to confirm that includes work correctly.
    # Also the fact that the #include "testinclude.h" above compiles.
    magic_value = 42

    stored = {}
    for repeat in range(2):
        for jitable in (234, 567): # Note different values than serial test
            # Each integer produces different code
            lib, factory, gettr = jit_integer(jitable, comm=comm, buildon=buildon, dijitso_root_dir=dijitso_root_dir)

            # Inspect values for testing
            assert jitable + magic_value == gettr(factory())

            # Memory cache test
            if repeat == 0:
                # Make a record of this lib
                stored[jitable] = lib
            else:
                # Check that we fetched the lib from the memory cache
                assert lib is stored[jitable]

    # If all went well we clean up, if assertions triggered
    # above we allow this cleanup to not happen
    shutil.rmtree(dijitso_root_dir, ignore_errors=True)
    comm.barrier()

# TODO: Cover various failure situations with tests
