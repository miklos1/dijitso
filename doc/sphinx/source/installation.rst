.. title:: Installation


============
Installation
============

DIJITSO is normally installed as part of an installation of FEniCS.
If you are using DIJITSO as part of the FEniCS software suite, it
is recommended that you follow the
`installation instructions for FEniCS
<https://fenics.readthedocs.io/en/latest/>`__.

To install DIJITSO itself, read on below for a list of requirements
and installation instructions.


Requirements and dependencies
=============================

DIJITSO requires Python version 2.7 or later and depends on the
following Python packages:

* six
* NumPy

These packages will be automatically installed as part of the
installation of DIJITSO, if not already present on your system.

Additionally, to run tests the following packages are needed

* pytest
* mpi4py (for running tests with mpi)


Installation instructions
=========================

To install DIJITSO, download the source code from the
`DIJITSO Bitbucket repository
<https://bitbucket.org/fenics-project/dijitso>`__,
and run the following command:

.. code-block:: console

    pip install .

To install to a specific location, add the ``--prefix`` flag
to the installation command:

.. code-block:: console

    pip install --prefix=<some directory> .
