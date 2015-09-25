dijitso
=======
*A Python module for distributed just-in-time shared library building*

Authors:

    - Martin Sandve Alnæs (martinal@simula.no)

Motivation
----------

This module was written to improve a core component of the FEniCS
framework, namely the just in time compilation of C++ code that is
generated from Python modules, but is only called from within a C++
library, and thus do not need wrapping in a nice Python interface.

The main approach of dijitso is to use ctypes to import the dynamic
shared library directly with no attempt at wrapping it in a Python
interface.

As long as the compiled code can provide a simple factory function to
a class implementing a predefined C++ interface, there is no limit to
the complexity of that interface as long as it is only called from C++
code, If you want a Python interface to your generated code, dijitso
is probably not the answer.

Although dijitso serves a very specific role within the FEniCS
project, it does not depend on other FEniCS components.

The parallel support depends on the mpi4py interface, although
mpi4py is not actually imported within the dijitso module so it
would be possible to mock the communicator object with a similar interface.

Feature list
------------

    - Disk cache system based on user provided signature string
      (user is responsible of the quality of the signature)

    - Lazy evaluation of possibly costly code generation through
      user-provided callback, called only if signature is not found in
      disk cache

    - Low overhead invocation of C++ compiler to produce a shared
      library with no Python wrapping

    - Portable shared library import using ctypes

    - Automatic compression of source code in the cache directory saves space

    - Autodetect which MPI processes share the same physical cache
      directory (doesn't matter if this is all cores on a node or
      shared across nodes with network mapped storage)

    - Automatic avoidance of race conditions in disk cache by
      only compiling on one process per physical cache directory

    - Optional MPI based distribution of shared library binary file

    - Configurable parallel behaviour:

        - "root": build only on single root node and distribute binary
          to each physical cache directory with MPI

        - "node": build on one process per physical cache directory

        - "process": build on each process, automatic separation of cache directories
