#!/usr/bin/env bash
set -e exit

echo Running tests in serial:
py.test

for p in 1 4 8 16; do
  echo Running tests with mpi, n=$p
  mpirun -n $p python -B -m pytest -svl
done
