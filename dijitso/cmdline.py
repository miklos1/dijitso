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

"""This is the commands executed from the commandline interface to dijitso.

Each function cmd_<cmdname> becomes a subcommand invoked by 'dijitso
cmdname ...args'.

The docstrings in the cmd_<cmdname> are shown on 'dijitso cmdname --help'.

The 'args' argument to cmd_* is a Namespace object with the commandline arguments.

"""

from __future__ import unicode_literals
from __future__ import print_function

from dijitso.params import validate_params

"""Use cases:

dijitso cp <signature>
<edit signature.cpp file, e.g. inserting debugging statements>
dijitso rm signature.so
dijitso add signature.cpp
dijitso build signature.cpp
"""


def cmd_config(args, params):
    "show configuration"
    params = validate_params(params)
    for category in sorted(params):
        print("%s:" % (category,))
        for name in sorted(params[category]):
            print("    %s: %s" % (name, params[category][name]))
    return 0


def _cmd_has(args, params):
    "check if file(s) exist in repository"
    print("has", args)
    return 0


def _cmd_show(args, params):
    "show file(s) in repository"
    print("show", args)
    return 0


def _cmd_grep(args, params):
    "grep content of file(s) in repository"
    print("grep", args)
    return 0


def _cmd_add(args=None):
    "add file(s) to repository"
    print("add", args)
    return 0


def _cmd_cp(args, params):
    "copy file(s) from repository"
    print("cp", args)
    return 0


def _cmd_rm(args, params):
    "remove file(s) from repository"
    print("rm", args)
    return 0


def _cmd_clean(args, params):
    "remove all files from repository"
    print("clean", args)
    return 0
