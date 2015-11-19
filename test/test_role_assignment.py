#!/usr/bin/env py.test
# -*- coding: utf-8 -*-
from __future__ import print_function
import pytest
from dijitso.system import makedirs
from dijitso.mpi import create_comms_and_role

@pytest.fixture()
def lib_dir0(comm):
    # Fake some common and some shared libdirs
    path = ".test_roles_%d" % (comm.rank,)
    makedirs(path)
    return path

@pytest.fixture()
def lib_dir2(comm):
    # Fake some common and some shared libdirs
    path = ".test_roles_%d_of_2" % (comm.rank % 2,)
    makedirs(path)
    return path

def test_role_root(comm, lib_dir2):
    buildon = "root"

    copy_comm, wait_comm, role = create_comms_and_role(comm, lib_dir2, buildon)

    if comm.rank == 0:
        expected_role = "builder"
    elif wait_comm.rank == 0:
        expected_role = "receiver"
    else:
        expected_role = "waiter"

    assert role == expected_role

    assert copy_comm is not None
    assert wait_comm is not None

    if role != "waiter":
        assert copy_comm.size == min(comm.size, 2)
    assert (comm.size//2) <= wait_comm.size <= (comm.size//2+1)

def test_role_node(comm, lib_dir2):
    buildon = "node"

    copy_comm, wait_comm, role = create_comms_and_role(comm, lib_dir2, buildon)

    if comm.rank in (0,1):
        expected_role = "builder"
    else:
        expected_role = "waiter"

    assert role == expected_role

    assert copy_comm is None
    assert wait_comm is not None

    assert (comm.size//2) <= wait_comm.size <= (comm.size//2+1)

def test_role_process(comm, lib_dir0):
    buildon = "process"

    copy_comm, wait_comm, role = create_comms_and_role(comm, lib_dir0, buildon)

    expected_role = "builder"

    assert role == expected_role

    assert copy_comm is None
    assert wait_comm is None
