#!/usr/bin/env bash
set -e exit

echo RUNNING SERIAL
py.test

while [ $? -eq 0 ]
do
  for p in 1 4 8; do
    echo RUNNING WITH p=$p
    mpirun -n $p python -B -m pytest -svl
  done
done
