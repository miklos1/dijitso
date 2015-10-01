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

"""Utilities for dijitso parameters."""

from six.moves import configparser
from dijitso.log import log, error
from glob import glob
import os

def discover_config_filename():
    basename = ".dijitso.conf"
    search_paths = [os.curdir, os.path.expanduser("~"), "/etc/dijitso", os.environ.get("DIJITSO_CONF")]
    for path in search_paths:
        names = glob(os.path.join(path, basename))
        if names:
            assert len(names) == 1
            return names[0]
    return None

_config_file_contents = None
def read_config_file():
    global _config_file_contents
    if _config_file_contents is None:
        filename = discover_config_filename()
        _config_file_contents = {}
        if filename is not None:
            parser = configparser.SafeConfigParser()
            parser.read(filename)
            for category in parser.sections():
                _config_file_contents[category] = {}
                for name, value in parser.items(category):
                    _config_file_contents[category][name] = value
    return _config_file_contents

def default_cache_params():
    p = dict(
        root_dir="~/.cache/dijitso",
        #tmp_dir="tmp",
        #err_dir="err",
        src_dir="src",
        lib_dir="lib",
        src_prefix="dijitso_",
        src_postfix=".cpp",
        src_storage="keep",
        lib_prefix="lib_dijitso_",
        lib_postfix=".so",
        )
    return p

def default_build_params():
    p = dict(
        cxx="g++",
        cxxflags=("-shared", "-fPIC", "-fvisibility=hidden"),
        cxxflags_debug=("-g", "-O0"),
        cxxflags_opt=("-O3",), # TODO: Improve optimization flags: vectorization, safe parts of fastmath flags, ...
        include_dirs=(),
        libs=(),
        debug=False,
        )
    return p

def default_generator_params():
    return {}

def default_params():
    p = dict(
        cache_params=default_cache_params(),
        build_params=default_build_params(),
        generator_params=default_generator_params(),
        )
    return p

_session_defaults = None
def session_default_params():
    global _session_defaults
    if _session_defaults is None:
        _session_defaults = validate_params()
    return _session_defaults.copy()

def as_str_tuple(p):
    """Convert p to a tuple of strings, allowing a list or tuple of strings or a single string as input."""
    if isinstance(p, str):
        return (p,)
    elif isinstance(p, (tuple, list)):
        if all(isinstance(item, str) for item in p):
            return p
    raise RuntimeError("Expecting a string or list of strings, not %s." % (p,))

def copy_params(params):
    "Copy two-level dict of params."
    return {k:v.copy() for k,v in params.items()}

def check_params_keys(default, params):
    "Check that keys in params exist in defaults."
    for category in params:
        if category not in default:
            error("Invalid parameter category '%s'." % category)
        if params[category] is not None:
            invalid = set(params[category]) - set(default[category])
            if invalid:
                error("Invalid parameter names %s in category '%s'." % (sorted(invalid), category))

def merge_params(default, params):
    "Merge two-level param dicts."
    p = {}
    for category in default:
        p[category] = default[category].copy()
        p[category].update(params.get(category, ()))
    return p

def validate_params(params):
    """Validate parameters to dijitso and fill in with defaults where missing."""

    # Start with defaults
    p = default_params()

    # Override with config file if any
    c = read_config_file()
    if c:
        check_params_keys(p, c)
        p = merge_params(p, c)

    # Override with runtime params if any
    if params:
        check_params_keys(p, params)
        p = merge_params(p, params)

    # Expand paths including "~" to include full user home directory path
    for category in p:
        for name, value in p[category].items():
            if name.endswith("_dir") and "~" in value:
                p[category][name] = os.path.expanduser(value)

    # Validate compiler flags format as tuple of strings
    bp = p["build_params"]
    for k in ("cxxflags", "cxxflags_debug", "cxxflags_opt", "include_dirs", "libs"):
        bp[k] = as_str_tuple(bp[k])

    return p
