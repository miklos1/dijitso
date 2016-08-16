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
from dijitso.system import get_status_output, lockfree_move_file, make_dirs
from dijitso.log import info, debug
from dijitso.cache import make_lib_dir, make_inc_dir, store_textfile
from dijitso.cache import create_lib_filename, create_lib_basename
from dijitso.cache import create_src_filename, create_src_basename
from dijitso.cache import create_inc_filename, create_inc_basename
from dijitso.cache import ensure_dirs
from dijitso.cache import compress_source_code


def make_unique(dirs):
    # NB! O(n^2) so use only on small data sets
    udirs = []
    for d in dirs:
        if d not in udirs:
            udirs.append(d)
    return tuple(udirs)


def make_compile_command(src_filename, lib_filename, dependencies,
                         build_params, cache_params):
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

    # Make all paths absolute
    include_dirs = [os.path.abspath(d) for d in include_dirs]
    lib_dirs = [os.path.abspath(d) for d in lib_dirs]
    rpath_dirs = [os.path.abspath(d) for d in rpath_dirs]

    # Add include dirs so compiler will find included headers
    args.extend("-I" + path for path in include_dirs)

    # Add library dirs so linker will find libraries
    args.extend("-L" + path for path in lib_dirs)

    # Add library dirs so runtime loader will find libraries
    args.extend("-Wl,-rpath," + path for path in rpath_dirs)

    # Add source filename
    args.append(src_filename)

    # Add dependencies to libraries to search for
    deplibs = tuple(create_lib_filename(depsig, cache_params)
                    for depsig in dependencies)
    args.extend("-l" + lib for lib in deplibs)

    # Add other external libraries to search for
    args.extend("-l" + lib for lib in build_params["libs"])

    return args


def compile_library(src_filename, lib_filename, dependencies, build_params,
                    cache_params):
    """Compile shared library from source file.

    Assumes source code resides in src_filename on disk.
    Calls compiler with configuration from build_params,
    to produce shared library in lib_filename.
    """
    # Build final command string
    cmd = make_compile_command(src_filename, lib_filename, dependencies,
                               build_params, cache_params)
    # cmds = " ".join(cmd)

    # Execute command
    status, output = get_status_output(cmd)

    return status, output


def temp_dir(build_params):
    "Return a temp directory."
    # TODO: Allow overriding with params
    return tempfile.mkdtemp()


def build_shared_library(signature, header, source, dependencies, params):
    """Build shared library from a source file and store library in cache."""
    cache_params = params["cache"]
    build_params = params["build"]

    # Create basenames
    inc_basename = create_inc_basename(signature, cache_params)
    src_basename = create_src_basename(signature, cache_params)
    lib_basename = create_lib_basename(signature, cache_params)

    # Create a temp directory and filenames within it
    tmpdir = temp_dir(build_params)
    temp_inc_filename = os.path.join(tmpdir, inc_basename)
    temp_src_filename = os.path.join(tmpdir, src_basename)
    temp_lib_filename = os.path.join(tmpdir, lib_basename)

    # Store source and header in temp dir
    if header:
        store_textfile(temp_inc_filename, header)
    store_textfile(temp_src_filename, source)

    # Build final command string
    cmd = make_compile_command(temp_src_filename, temp_lib_filename,
                               dependencies, build_params, cache_params)
    # cmds = " ".join(cmd)

    # Execute command to compile generated source code to dynamic
    # library
    status, output = get_status_output(cmd)

    # Move files to cache on success or a local dir on failure
    if status == 0:
        # Create final filenames in cache dirs
        ensure_dirs(cache_params)
        inc_filename = create_inc_filename(signature, cache_params)
        src_filename = create_src_filename(signature, cache_params)
        lib_filename = create_lib_filename(signature, cache_params)
        assert os.path.exists(os.path.dirname(inc_filename))
        assert os.path.exists(os.path.dirname(src_filename))
        assert os.path.exists(os.path.dirname(lib_filename))

        # Move inc,src,lib files to cache using safe lockfree move
        if header:
            lockfree_move_file(temp_inc_filename, inc_filename)
        lockfree_move_file(temp_src_filename, src_filename)
        lockfree_move_file(temp_lib_filename, lib_filename)

        # Compress or delete source code based on params
        # TODO: Better to do this before moving to cache
        compress_source_code(src_filename, cache_params)

        debug("Compilation succeeded. Logs, includes, sources, "
              "and binary have been written to: %s, %s, %s"
              % (inc_filename, src_filename, lib_filename))

    else:
        # Create filenames in a local directory to store files for
        # reproducing failure
        fail_dir = os.path.abspath(os.path.join("jitfailure-" + signature))
        make_dirs(fail_dir)
        inc_filename = os.path.join(fail_dir, inc_basename)
        src_filename = os.path.join(fail_dir, src_basename)
        cmd_filename = os.path.join(fail_dir, "command")
        log_filename = os.path.join(fail_dir, "error.log")
        lib_filename = None  # This is returned below!

        # Move inc,src files to fail_dir using safe lockfree move
        if header:
            lockfree_move_file(temp_inc_filename, inc_filename)
        lockfree_move_file(temp_src_filename, src_filename)

        # Write compile command to failure dir, adjusted to use local
        # source file
        cmd = make_compile_command(src_basename, lib_basename, dependencies,
                                   build_params, cache_params)
        cmds = " ".join(cmd)
        store_textfile(cmd_filename, cmds)

        # Write compiler output to failure dir
        store_textfile(log_filename, output)

        info("Compilation failed! Sources, command, and "
             "errors have been written to: %s" % (fail_dir,))

    return status, output, lib_filename
