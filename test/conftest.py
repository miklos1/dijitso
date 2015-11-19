#!/usr/bin/env py.test
# -*- coding: utf-8 -*-
from __future__ import print_function
import pytest
import hashlib, os
import dijitso
import ctypes


@pytest.fixture()
def comm():
    try:
        from mpi4py import MPI
        c = MPI.COMM_WORLD
    except:
        c = None
    return c


_code_template_params = """\
/**
Arguments used to generate this code:
%(generator_params)s
*/
"""

_code_template_defines = """\
// Based on https://gcc.gnu.org/wiki/Visibility
#if defined _WIN32 || defined __CYGWIN__
    #ifdef __GNUC__
        #define DLL_EXPORT extern "C" __attribute__ ((dllexport))
    #else
        #define DLL_EXPORT extern "C" __declspec(dllexport)
    #endif
#else
    #define DLL_EXPORT extern "C" __attribute__ ((visibility ("default")))
#endif
"""

_code_template_interface = """\
// This would be '#include <ufc.h>'
class %(interfacename)s
{
public:
    virtual ~%(interfacename)s() {}

    virtual int get_test_value() const = 0;
};
"""

_code_template_class = """\
/// This would be the generated ufc::form code
class %(classname)s: public %(interfacename)s
{
public:
    int get_test_value() const
    { return %(testvalue)s; }
};
"""

_code_template_factory = """\
/// Construct an object of class %(classname)s without any class interface wrapping
DLL_EXPORT void * create_%(signature)s()
{
    return new %(classname)s();
}
"""

_code_template_testhook = """\
#include "testinclude.h"
DLL_EXPORT int get_test_value_%(testvalue)d(void * p)
{
    %(interfacename)s * pp = static_cast<%(interfacename)s *>(p);
    int v = pp->get_test_value();
    return v + TESTINCLUDE_MAGIC_VALUE;
}
"""

def generate(signature, jitable, generator_params):
    """."""
    code_parts = dict(
        generator_params=str(generator_params),
        signature=signature,
        classname="class_%s" % (jitable,),
        interfacename="external_interface",
        testvalue=jitable,
        )
    parts = [
        _code_template_params % code_parts,
        _code_template_defines % code_parts,
        _code_template_interface % code_parts,
        _code_template_class % code_parts,
        _code_template_factory % code_parts,
        _code_template_testhook % code_parts,
        ]
    code = '\n'.join(parts)
    return code


def _jit_integer(jitable, comm=None, buildon="node", dijitso_root_dir=".dijitso"):
    "A mock jit routine setup to exercise much of the library."

    # Setup params
    cache_params = dict(
        root_dir=dijitso_root_dir,
        src_storage="compress",
        )
    build_params = dict(
        debug=True,
        include_dirs=("testincludes",),
        )
    generator_params = None
    params = dict(
        cache_params=cache_params,
        build_params=build_params,
        generator_params=generator_params,
        )
    params = dijitso.validate_params(params)

    # Compute a signature
    h = hashlib.sha1()
    h.update(repr(jitable))
    h.update(repr(build_params))
    h.update(repr(generator_params))
    signature = h.hexdigest()[:10]

    # Autodetect subcomms and role based on buildin option and physical disk access of processes
    from dijitso.mpi import create_comms_and_role, send_binary, receive_binary
    from dijitso.system import makedirs
    sync_dir = os.path.join(dijitso_root_dir, "sync")
    makedirs(sync_dir)
    copy_comm, wait_comm, role = create_comms_and_role(comm, sync_dir, buildon)

    # Somewhat messy definitions of send/receive/wait...
    if copy_comm is None:
        send = None
        receive = None
    else:
        def send(lib_data):
            assert role == "builder"
            send_binary(copy_comm, lib_data)
        if role == "builder":
            receive = None
        else:
            def receive():
                assert role == "receiver"
                return receive_binary(copy_comm)
    if wait_comm is None:
        wait = None
    else:
        def wait():
            wait_comm.barrier()

    # Jit it!
    lib = dijitso.jit(signature, jitable, params,
                      generate, send, receive, wait)

    # Extract the factory function we want from library
    factory = dijitso.extract_factory_function(lib, "create_" + signature)
    # ... and the test specific getter function
    get_test_value = getattr(lib, "get_test_value_%d" % jitable)
    get_test_value.argtypes = [ctypes.c_void_p]
    get_test_value.restype = ctypes.c_int

    # Return both library and factory
    return lib, factory, get_test_value

@pytest.fixture()
def jit_integer():
    return _jit_integer
