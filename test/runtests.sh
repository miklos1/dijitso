#!/usr/bin/env bash
set -e exit
echo RUNNING SERIAL
#py.test
for p in 1 2 3 7 8; do
#for p in 3; do
  echo RUNNING WITH p=$p
  mpirun -n $p python -B -m pytest
done
