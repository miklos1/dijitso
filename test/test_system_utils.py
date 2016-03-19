
import os
import uuid
from dijitso.system import lockfree_move_file, get_status_output, delete_file


def test_get_status_output():
    pass  # FIXME


def test_lockfree_move_file():
    # Running this loop in multiple processes with mpi is perhaps a decent test?
    tmpdir = "."

    # source is different for each process and loop iteration
    n = 3
    u = uuid.uuid4().int
    srcs = [os.path.join(tmpdir, "test_lockfree_move_file-%d.src-%d" % (u, i))
            for i in range(n)]

    # fixed destination
    dst = os.path.join(tmpdir, "test_lockfree_move_file.dst")
    #delete_file(dst)  # can't do this when testing with mpi!

    for src in srcs:
        with open(src, "w") as f:
            f.write("dummy")
        assert os.path.exists(src)
        lockfree_move_file(src, dst)
        assert os.path.exists(dst)
        assert not os.path.exists(src)

    with open(dst) as f:
        dummy = f.read()
    assert dummy == "dummy"
