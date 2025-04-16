#!/bin/bash -l

#PBS -P es60
#PBS -q normal
#PBS -l walltime=5:00:00
#PBS -l mem=100GB
#PBS -l ncpus=3024
#PBS -l jobfs=10GB
#PBS -l wd
#PBS -l storage=scratch/es60+gdata/es60
#PBS -j oe

conda activate tabular_oceans

python ./add_iquod_flags_to_raggedWOD.py
