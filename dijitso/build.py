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

"""Utilities for building libraries with dijitso."""

from __future__ import unicode_literals

import tempfile
import os
import shutil
from dijitso.system import get_status_output
from dijitso.log import log, error
from dijitso.cache import create_lib_filename, create_lib_basename, make_lib_dir, make_inc_dir


def make_unique(dirs):
    # NB! O(n^2) so use only on small data sets
    udirs = []
    for d in dirs:
        if d not in udirs:
            udirs.append(d)
    return tuple(udirs)


def make_compile_command(src_filename, lib_filename, build_params, cache_params):
    """Piece together the compile command from build params.

    Returns the command as a list with the command and its arguments.
    """
    # Get compiler name
    args = [build_params["cxx"]]

    # Set output name
    args.append("-o" + lib_filename)

    # Build options (defaults assume gcc compatibility)
    args.extend(build_params["cxxflags"])
    if build_params["debug"]:
        args.extend(build_params["cxxflags_debug"])
    else:
        args.extend(build_params["cxxflags_opt"])

    # Get dijitso dirs based on cache_params
    inc_dir = make_inc_dir(cache_params)
    lib_dir = make_lib_dir(cache_params)

    # Add dijitso directories to includes, libs, and rpaths
    include_dirs = make_unique(build_params["include_dirs"] + (inc_dir,))
    lib_dirs = make_unique(build_params["lib_dirs"] + (lib_dir,))
    rpath_dirs = make_unique(build_params["rpath_dirs"] + (lib_dir,))
    
    # Add include dirs so compiler will find included headers
    args.extend("-I"+path for path in include_dirs)

    # Add library dirs so linker will find libraries
    args.extend("-L"+path for path in lib_dirs)

    # Add library dirs so runtime loader will find libraries
    args.extend("-Wl,-rpath,"+path for path in rpath_dirs)

    # Add source filename
    args.append(src_filename)

    # Add libraries to search for
    args.extend("-l"+lib for lib in build_params["libs"])

    return args


def compile_library(src_filename, lib_filename, build_params, cache_params):
    """Compile shared library from source file.

    Assumes source code resides in src_filename on disk.
    Calls compiler with configuration from build_params,
    to produce shared library in lib_filename.
    """
    # Build final command string
    cmd = make_compile_command(src_filename, lib_filename, build_params, cache_params)
    cmds = " ".join(cmd)

    # Execute command
    # TODO: Capture compiler output and log it to .dijitso/log/
    # TODO: Parse compiler output to find error(s) for better error messages.
    status, output = get_status_output(cmd)

    # Failure to compile is usually a showstopper
    if status:
        error("Compile command\n  %s\nfailed with code %d:\n%s" % (cmds, status, output))
    #return status


def build_shared_library(signature, src_filename, dependencies, params):
    """Build shared library from a source file and store library in cache."""
    # Create a safe temp directory and a library filename in there
    tmp = tempfile.mkdtemp()
    cache_params = params["cache"]
    temp_lib_filename = os.path.join(tmp, create_lib_basename(signature, cache_params))

    # Add dependencies to build libs list
    build_params = dict(params["build"])
    if dependencies:
        deplibs = tuple(create_lib_filename(depsig, cache_params) for depsig in dependencies)
        build_params["libs"] = build_params["libs"] + deplibs

    # Compile generated source code to dynamic library
    compile_library(src_filename, temp_lib_filename, build_params, cache_params)

    # Move compiled library to cache
    # Prepare target directory and filename for library
    make_lib_dir(cache_params)
    lib_filename = create_lib_filename(signature, cache_params)
    if temp_lib_filename != lib_filename:
        shutil.move(temp_lib_filename, lib_filename)

    return lib_filename
