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

"""Utilities for building libraries with dijitso."""

from __future__ import print_function

from dijitso.system import makedirs, get_status_output
from dijitso.log import log, error
from dijitso.cache import create_lib_filename

def make_compile_command(src_filename, lib_filename, build_params):
    """Piece together the compile command from build params.

    Returns the command as a list with the command and its arguments.
    """
    # Get compiler name
    args = [build_params["cxx"]]

    # Build options (defaults assume gcc compatibility)
    args.extend(build_params["cxxflags"])
    if build_params["debug"]:
        args.extend(build_params["cxxflags_debug"])
    else:
        args.extend(build_params["cxxflags_opt"])

    # Add include dirs
    args.extend("-I"+inc for inc in build_params["include_dirs"])

    # Add libraries TODO: Is this necessary with shared libraries?
    args.extend("-L"+inc for inc in build_params["libs"])

    # Add filenames
    args.append("-o" + lib_filename)
    args.append(src_filename)

    return args

def compile_library(src_filename, lib_filename, build_params):
    """Compile shared library from source file.

    Assumes source code resides in src_filename on disk.
    Calls compiler with configuration from build_params,
    to produce shared library in lib_filename.
    """
    # Build final command string
    cmd = " ".join(make_compile_command(src_filename, lib_filename, build_params))

    # Execute command
    # TODO: Capture compiler output and log it to .dijitso/err/
    # TODO: Parse compiler output to find error(s) for better error messages.
    status, output = get_status_output(cmd)

    # Failure to compile is usually a showstopper
    if status:
        error("Compile command\n  %s\nfailed with code %d:\n%s" % (cmd, status, output))

    return status

def build_shared_library(signature, src_filename, params):
    """Build shared library from a source file and store library in cache."""
    # TODO: Currently compiling directly into dijitso lib dir. Use temp dir and move on success.

    # Prepare target directory and filename for library
    makedirs(params["cache_params"]["lib_dir"])
    lib_filename = create_lib_filename(signature, params["cache_params"])

    # Compile generated source code to dynamic library
    compile_library(src_filename, lib_filename, params["build_params"])

    return lib_filename
