#!/bin/bash -l

#PBS -P es60
#PBS -q normal
#PBS -l walltime=5:00:00
#PBS -l mem=190GB
#PBS -l ncpus=48
#PBS -l jobfs=400GB
#PBS -l wd
#PBS -l storage=scratch/es60+gdata/es60
#PBS -j oe

. /g/data/es60/rlc599/venvs/cars/bin/activate

python3 ~/cars-v2/src/features/add_iquod_flags_to_raggedWOD.py
