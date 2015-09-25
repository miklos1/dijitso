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
import os, errno, ctypes, gzip, shutil, uuid
from glob import glob
import numpy

def makedirs(path):
    """Creates a directory (tree). If directory already exists it does nothing."""
    try:
        os.makedirs(path)
    except os.error as e:
        if e.errno != errno.EEXIST:
            raise

def deletefile(filename):
    """Remove a file. If the file is not there it does nothing."""
    try:
        os.remove(filename)
    except os.error as e:
        if e.errno != errno.ENOENT:
            raise

def as_str_tuple(p):
    """Convert p to a tuple of strings, allowing a list or tuple of strings or a single string as input."""
    if isinstance(p, str):
        return (p,)
    elif isinstance(p, (tuple, list)):
        if all(isinstance(item, str) for item in p):
            return p
    raise RuntimeError("Expecting a string or list of strings, not %s." % (p,))


def log(msg): # TODO: Replace with proper logging
    print(msg)

def error(msg):
    raise RuntimeError(msg)


def default_cache_params():
    p = dict(
        #tmp_dir=".dijitso/tmp",
        #err_dir=".dijitso/err",
        src_dir=".dijitso/src",
        lib_dir=".dijitso/lib",
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
    # TODO: Allow overriding default parameters from config file
    p = dict(
        cache_params=default_cache_params(),
        build_params=default_build_params(),
        generator_params=default_generator_params(),
        )
    return p

def validate_params(params):
    """Validate parameters to dijitso and fill in with defaults where missing."""
    # TODO: Assuming a two-layer structure here, we can do better if needed

    # Just use defaults if we get nothing
    p = default_params()
    if not params:
        return p

    # Start with defaults and override with given,
    # also checking that keys in params are valid
    for category in params:
        if category not in p:
            error("Invalid parameter category %s." % category)
        if params[category] is not None:
            for name in params[category]:
                if name not in p[category]:
                    error("Invalid parameter name %s in category %s." % (name, category))
                else:
                    # Override default value with given value
                    p[category][name] = params[category][name]

    # Validate compiler flags storage
    bp = p["build_params"]
    for k in ("cxxflags", "cxxflags_debug", "cxxflags_opt", "include_dirs", "libs"):
        bp[k] = as_str_tuple(bp[k])
    return p


def create_src_filename(signature, cache_params):
    "Create source code filename based on signature and params."
    basename = cache_params["src_prefix"] + signature + cache_params["src_postfix"]
    return os.path.join(cache_params["src_dir"], basename)

def create_lib_filename(signature, cache_params):
    "Create library filename based on signature and params."
    basename = cache_params["lib_prefix"] + signature + cache_params["lib_postfix"]
    return os.path.join(cache_params["lib_dir"], basename)


def load_library(signature, cache_params):
    """Load existing dynamic library from disk.

    Returns library module if found, otherwise None.

    If found, the module is placed in memory cache for later lookup_lib calls.
    """
    lib_filename = create_lib_filename(signature, cache_params)
    if not os.path.exists(lib_filename):
        return None
    try:
        lib = ctypes.cdll.LoadLibrary(lib_filename)
    except os.error as e:
        error("Failed to load library %s." % (lib_filename,))

    if lib is not None:
        # Disk loading succeeded, register loaded library in memory cache for next time
        _lib_cache[signature] = lib
    return lib

_lib_cache = {}
def lookup_lib(signature, cache_params):
    """Lookup library in memory cache then in disk cache.

    Returns library module if found, otherwise None.
    """
    # Look for already loaded library in memory cache
    lib = _lib_cache.get(signature)
    if lib is None:
        # Cache miss in memory, try looking on disk
        lib = load_library(signature, cache_params)
    # Return library or None
    return lib

def store_src(signature, src, cache_params):
    "Store source code in file within dijitso directories."
    makedirs(cache_params["src_dir"])
    src_filename = create_src_filename(signature, cache_params)

    if not os.path.exists(src_filename):
        # Expected behaviour: just write the code to file
        with open(src_filename, "w") as f:
            f.write(src)
    else:
        # Error handling if the file was already there
        with open(src_filename, "r") as f:
            found_src = f.read()
        if found_src != src:
            # If the existing source code file has different content, fail
            # after writing new and different source to file with .newer suffix
            with open(src_filename + ".new", "w") as f:
                f.write(src)
            error("File\n  %s\nalready exists and its contents are different.\n"
                  "The new source code has been written to\n  %s" % (src_filename, src_filename+".new"))
    return src_filename

def generate_source_code(signature, generator, jitable, params):
    """Generate source code and store in dijitso cache."""
    # Generate source code
    src = generator(signature, jitable, params["generator_params"])

    # Store source code in dijitso src dir
    src_filename = store_src(signature, src, params["cache_params"])

    # Return filename for use in compile step
    return src_filename

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
    # TODO: Execute compiler command with popen? Check what's used from instant. Make it configurable.
    # TODO: Capture compiler output and log it to .dijitso/err/
    # TODO: Parse compiler output to find error(s) for better error messages.
    status = os.system(cmd)

    # Failure to compile is usually a showstopper
    if status:
        error("Compile command failed with code %d:\n    %s" % (status, cmd))

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

def compress_source_code(src_filename, cache_params):
    # Keep, delete or compress source code
    src_storage = cache_params["src_storage"]
    if src_storage == "keep":
        pass
    elif src_storage == "delete":
        deletefile(src_filename)
    elif src_storage == "compress":
        with open(src_filename, "rb") as f_in, gzip.open(src_filename + ".gz", "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)
        deletefile(src_filename)
    else:
        error("Invalid src_storage parameter. Expecting 'keep', 'delete', or 'compress'.")

def bcast_uuid(comm):
    "Create a unique id shared across all processes in comm."
    guid = numpy.ndarray((1,), dtype=numpy.uint64)
    if comm.rank == 0:
        # uuid creates a unique 128 bit id, we just pick the low 64 bits
        guid[0] = numpy.uint64(uuid.uuid4().int & ((1<<64)-1))
    comm.Bcast(guid, root=0)
    return int(guid[0])

def discover_path_access_ranks(comm, path):
    """Discover which ranks share access to the same directory.

    This cannot be done by comparing paths, because
    a path string can represent a local work directory
    or a network mapped directory, depending on cluster
    configuration.

    Current approach is that each process touches a
    filename with its own rank in their given path.
    By reading in the filelist from the same path,
    we'll find which ranks have access to the same
    directory.

    To avoid problems with leftover files from previous
    program crashes, or collisions between simultaneously
    running programs, we use a random uuid in the filenames
    written.
    """
    # Create a unique basename for rank files of this program
    guid = bcast_uuid(comm) # TODO: Run this in an init function and store for program duration?
    basename = os.path.join(path, "rank.%d." % guid)

    # Write the rank of this process to a filename
    filename = basename + str(comm.rank)
    with open(filename, "w") as f:
        f.write("")

    # Wait for all writes to take place. Don't know how robust this is with nfs!!!
    comm.Barrier()

    # Read filelist
    noderanks = sorted([int(fn.replace(basename, "")) for fn in glob(basename+"*")])

    # Wait for everyone to finish reading filelist
    comm.Barrier()

    # Clean up our own rank file. If the process is aborted,
    # this may fail to happen and leave a dangling file!
    # However the file takes no space, and the guid ensures
    # it won't be a problem.
    # TODO: Include a gc command in dijitso to clean up this and other stuff.
    os.remove(filename)
    return noderanks

def gather_global_partitions(comm, partition):
    """Gather an ordered list of unique partition values within comm."""
    global_partitions = numpy.ndarray((comm.size,), dtype=numpy.uint64)
    local_partition = numpy.ndarray((1,), dtype=numpy.uint64)
    local_partition[0] = partition
    comm.Allgather(local_partition, global_partitions)
    return sorted(set(global_partitions))

def create_subcomm(comm, ranks):
    "Create a communicator for a set of ranks."
    group = comm.Get_group()
    subgroup = group.Incl(ranks)
    subcomm = comm.Create(subgroup)
    subgroup.Free()
    group.Free()
    return subcomm

def create_node_comm(comm, lib_dir):
    """Create comms for communicating within a node."""
    # Find ranks that share this physical lib_dir (physical dir, not same path string)
    node_ranks = discover_path_access_ranks(comm, lib_dir)

    # Partition comm into one communicator for each physical lib_dir
    assert len(node_ranks) >= 1
    node_root = min(node_ranks)
    node_comm = comm.Split(node_root, node_ranks.index(comm.rank))
    return node_comm, node_root

def create_node_roots_comm(comm, node_root):
    """Build comm for communicating among the node roots."""
    unique_global_node_roots = gather_global_partitions(comm, node_root)
    roots_comm = create_subcomm(comm, unique_global_node_roots)
    return roots_comm

def create_comms_and_role(comm, lib_dir, buildon):
    """Determine which role each process should take, and create
    the right copy_comm and wait_comm for the build strategy.

    buildon must be one of "root", "node", or "process".
    """
    assert buildon in ("root", "node", "process")

    if comm is None:
        return None, None, "builder"

    # Now assign values to the copy_comm, wait_comm, and role, depending on buildon strategy chosen
    if buildon == "root":
        # Approach: global root builds and sends binary to node roots, everyone waits on their node group
        node_comm, node_root = create_node_comm(comm, lib_dir)
        roots_comm = create_node_roots_comm(comm, node_root)

        copy_comm = roots_comm
        wait_comm = node_comm
        if comm.rank == 0:
            role = "builder"
        elif node_comm.rank == 0:
            assert comm.rank == node_root
            role = "receiver"
        else:
            assert comm.rank != node_root
            role = "waiter"

    elif buildon == "node":
        # Approach: each node root builds, everyone waits on their node group
        node_comm, node_root = create_node_comm(comm, lib_dir)

        copy_comm = None
        wait_comm = node_comm
        if node_comm.rank == 0:
            assert comm.rank == node_root
            role = "builder"
        else:
            assert comm.rank != node_root
            role = "waiter"

    elif buildon == "process":
        # Approach: each process builds its own module, no communication.
        # To ensure no race conditions in this case independently of cache dir setup,
        # we include an error check on the size of the autodetected node_comm.
        # This should always be 1, or we provide the user with an informative message.
        # TODO: Append program uid and process rank to basedir instead?
        node_comm, node_root = create_node_comm(comm, lib_dir)

        if node_comm.size > 1:
            error("Asking for per-process building but processes share cache dir."
                  " Please configure dijitso dirs to be distinct per process.")

        copy_comm = None
        wait_comm = None
        assert node_comm.rank == 0
        assert comm.rank == node_root
        role = "builder"

    else:
        # unused
        # Approach: global root builds and sends to everyone else
        copy_comm = comm
        wait_comm = None
        role = "builder" if comm.rank == 0 else "receiver"

    return copy_comm, wait_comm, role

def send_library(comm, lib_filename, params):
    "Send compiled library as binary blob over MPI."
    import numpy

    # TODO: Test this in parallel locally.
    # TODO: Test this in parallel on clusters.
    # http://mpi4py.scipy.org/docs/usrman/tutorial.html

    # Check that we are the root
    root = 0
    assert comm.rank == root

    # Read library from cache as binary file
    lib_data = numpy.fromfile(lib_filename, dtype=numpy.uint8)

    # Send file size
    lib_size = numpy.ndarray((1,), dtype=numpy.uint32)
    lib_size[0] = lib_data.shape[0]
    log("rank %d: send size with root=%d." % (comm.rank, root))
    comm.Bcast(lib_size, root=root)

    # Send file contents
    log("rank %d: send data with root=%d." % (comm.rank, root))
    comm.Bcast(lib_data, root=root)

def receive_library(comm, signature, cache_params):
    "Store shared library received as a binary blob to cache."
    import numpy

    # Check that we are not the root
    root = 0
    assert comm.rank != root

    # Receive file size
    lib_size = numpy.ndarray((1,), dtype=numpy.uint32)
    log("rank %d: receive size with root=%d." % (comm.rank, root))
    comm.Bcast(lib_size, root=root)

    # Receive file contents
    lib_data = numpy.ndarray(lib_size[0], dtype=numpy.uint8)
    log("rank %d: receive data with root=%d." % (comm.rank, root))
    comm.Bcast(lib_data, root=root)

    # Store to cache dir
    lib_filename = create_lib_filename(signature, cache_params)
    makedirs(cache_params["lib_dir"])
    lib_data.tofile(lib_filename)
    # TODO: Set permissions?

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
    # Look for library in memory or disk cache
    cache_params = params["cache_params"]
    lib = lookup_lib(signature, cache_params)

    if lib is None:
        # Since we didn't find the library in cache, we must build it.

        # TODO: Should call these once (for each comm at least) globally in dolfin, not on each jit call
        #copy_comm, wait_comm, role = create_comms_and_role(comm, cache_params["lib_dir"], buildon)

        if role == "builder":
            # 1) Generate code and store in cache
            src_filename = generate_source_code(signature, generator, jitable, params)

            # 2) Compile shared library and store in cache
            lib_filename = build_shared_library(signature, src_filename, params)

            # 3) Send library over network if we have a copy_comm
            if copy_comm is not None and copy_comm.size > 1:
                send_library(copy_comm, lib_filename, params)

            # Locally compress or delete source code based on params
            compress_source_code(src_filename, cache_params)

        elif role == "receiver":
            # 3) Get library as binary blob over MPI and store in cache
            assert copy_comm is not None
            receive_library(copy_comm, signature, cache_params)

        elif role == "waiter":
            # Do nothing
            pass

        else:
            error("Invalid role %s" % (role,))

        # 4) Notify waiting processes that we're done
        if wait_comm is not None:
            wait_comm.Barrier()

        # Finally load library from disk cache (places in memory cache)
        lib = load_library(signature, cache_params)

    # Return library
    return lib

def extract_factory_function(lib, name):
    """Extract function from loaded library.

    Assuming signature "(void *)()", for anything else use look at ctypes documentation.

    Returns the factory function or raises error.
    """
    function = getattr(lib, name)
    function.restype = ctypes.c_void_p
    return function
