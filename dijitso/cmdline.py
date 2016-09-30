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

"""This file contains the commands available through command-line dijitso-cache.

Each function cmd_<cmdname> becomes a subcommand invoked by::

    dijitso-cache cmdname ...args

The docstrings in the cmd_<cmdname> are shown when running::

    dijitso-cache cmdname --help

The 'args' argument to cmd_* is a Namespace object with the commandline arguments.

"""

from __future__ import unicode_literals
from __future__ import print_function

import os
import re
import sys
from glob import glob

from dijitso.params import validate_params
from dijitso.cache import glob_cache, grep_cache
from dijitso.cache import create_lib_filename
from dijitso.cache import extract_lib_signatures
from dijitso.cache import extract_files


"""Use cases:

dijitso-cache cp <signature>
<edit signature.cpp file, e.g. inserting debugging statements>
dijitso-cache c rm signature.so
dijitso-cache c add signature.cpp
dijitso-cache c build signature.cpp
"""


def cmd_config(args, params):
    "show configuration"
    params = validate_params(params)
    print("Showing default flags for dijitso:")
    for category in sorted(params):
        # Skip empty categories
        if not params[category]:
            continue
        print("%s:" % (category,))
        for name in sorted(params[category]):
            value = params[category][name]
            # Compiler flags etc are more useful in space separated form:
            if isinstance(value, tuple):
                value = " ".join(value)
            print("    %s: %s" % (name, value))
    return 0


def cmd_show(args, params):
    "show lists of files in cache"
    params = validate_params(params)

    # FIXME: Get command-line arguments to configure this
    verbose = True
    show_summaries = True
    show_signatures = False
    show_inc = True
    show_log = True
    show_lib = True
    show_src = True

    cache_params = params["cache"]
    gc = glob_cache(cache_params)

    if show_signatures:
        sigs = extract_lib_signatures(cache_params)
        if show_summaries:
            print("Library signatures (%d):" % len(sigs))
        for s in sorted(sigs):
            print("\t" + s)
    else:
        if show_inc:
            g = gc["inc"]
            if show_summaries:
                print("Include files: %d" % len(g))
            if verbose:
                for f in sorted(g):
                    print("\t" + f)
        if show_src:
            g = gc["src"]
            if show_summaries:
                print("Source files: %d" % len(g))
            if verbose:
                for f in sorted(g):
                    print("\t" + f)
        if show_log:
            g = gc["log"]
            if show_summaries:
                print("Log files: %d" % len(g))
            if verbose:
                for f in sorted(g):
                    print("\t" + f)
        if show_lib:
            g = gc["lib"]
            if show_summaries:
                print("Library files: %d" % len(g))
            if verbose:
                for f in sorted(g):
                    print("\t" + f)

    return 0


def cmd_clean(args, params):
    "remove files from cache"
    params = validate_params(params)

    # FIXME: Get command-line arguments
    dryrun = False
    use_inc = True
    use_src = True
    use_lib = True
    use_log = True

    categories = []
    if use_inc:
        categories.append("inc")
    if use_src:
        categories.append("src")
    if use_lib:
        categories.append("lib")
    if use_log:
        categories.append("log")

    gc = glob_cache(cache_params, categories=categories)
    for category in gc:
        for fn in gc[category]:
            if dryrun:
                print("rm %s" % (fn,))
            else:
                try_delete_file(fn)
    return 0


def cmd_grep(args, params):
    "grep content of header and source file(s) in cache"
    params = validate_params(params)
    cache_params = params["cache"]

    # FIXME: Get command-line arguments
    pattern = "create"
    regexmode = False
    linenumbers = True
    countonly = False
    filesonly = False
    use_inc = True
    use_src = True
    use_lib = False
    use_log = False

    categories = []
    if use_inc:
        categories.append("inc")
    if use_src:
        categories.append("src")
    if use_lib:
        categories.append("lib")
    if use_log:
        categories.append("log")

    if not regexmode:
        pattern = ".*(" + pattern + ").*"
    regex = re.compile(pattern)
    allmatches = grep_cache(regex, cache_params,
                            linenumbers=linenumbers, countonly=countonly,
                            categories=categories)
    if filesonly:
        print("\n".join(sorted(allmatches)))
    elif countonly:
        print("\n".join("%s: %d" % (k, v) for k, v in sorted(allmatches.items())))
    else:
        for fn in sorted(allmatches):
            print("File '%s' matches:" % (fn,))
            print("\n".join(allmatches[fn]))
    return 0


def cmd_grepfunction(args, params):
    "grep content source file(s) in cache"
    params = validate_params(params)
    cache_params = params["cache"]

    # FIXME: Get command-line arguments
    pattern = "create"
    regexmode = False
    linenumbers = True
    countonly = False
    filesonly = False

    categories = ["src"]

    if not regexmode:
        pattern = ".*(" + pattern + ").*"
    regex = re.compile(pattern)
    allmatches = grep_cache(regex, cache_params,
                            linenumbers=linenumbers, countonly=countonly,
                            categories=categories)
    if filesonly:
        print("\n".join(sorted(allmatches)))
    elif countonly:
        print("\n".join("%s: %d" % (k, v) for k, v in sorted(allmatches.items())))
    else:
        for fn in sorted(allmatches):
            print("File '%s' matches:" % (fn,))
            print("\n".join(allmatches[fn]))
    return 0


def cmd_checkout(args, params):
    "copy files from cache to a directory"
    params = validate_params(params)

    # FIXME: Get command-line arguments
    signature = "ffc_form_2c63bd5aaebb630a44ae10a481d6a67677ec9b05"
    prefix = "jit-checkout-"
    path = os.curdir
    use_inc = True
    use_src = True
    use_lib = True
    use_log = True

    categories = []
    if use_inc:
        categories.append("inc")
    if use_src:
        categories.append("src")
    if use_lib:
        categories.append("lib")
    if use_log:
        categories.append("log")

    path = extract_files(signature, params, prefix=prefix, path=path,
                         categories=categories)
    print("Extracted files to '%s'." % (path,))
    return 0
