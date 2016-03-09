#!/usr/bin/env bash
set -e exit

echo Running tests in serial:
export MYRANK=serial
export MPISIZE=0
python -B -m pytest -svl --cov-report html --cov=dijitso

for p in 1 4 8 16; do
  echo Running tests with mpi, n=$p
  export MPISIZE=$p
  mpirun -n $p ./mpipytest.sh
done
