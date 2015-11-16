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

def test_core_jit_framework(jit_integer):
    """Jit a simple code generated by inserting a simple integer.

    Covers (if the cache is initially empty):

        - memory cache miss
        - memory cache hit
        - compiling
        - loading
        - factory function extraction

    """

    # This magic value is defined in testincludes/testinclude.h,
    # so this is used to confirm that includes work correctly.
    # Also the fact that the #include "testinclude.h" above compiles.
    magic_value = 42

    stored = {}
    for repeat in range(2):
        for jitable in (123, 456):
            # Each integer produces different code
            lib, factory, gettr = jit_integer(jitable)

            # Inspect values for testing
            assert jitable + magic_value == gettr(factory())

            # Memory cache test
            if repeat == 0:
                # Make a record of this lib
                stored[jitable] = lib
            else:
                # Check that we fetched the lib from the memory cache
                assert lib is stored[jitable]

# TODO: Cover various failure situations with tests
