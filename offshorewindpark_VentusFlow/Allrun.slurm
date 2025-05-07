#!/bin/bash

### SLURM script for running the offshore wind park simulation in parallel
### HLRS, 2024-2025

#SBATCH --partition=compute                     ### Partition
#SBATCH --job-name=openfoamsimoffshore          ### Job Name
#SBATCH --time=512:00:00                        ### WallTime
#SBATCH --mem-per-cpu 2G
#SBATCH --ntasks 120
#SBATCH --ntasks-per-core 2
#SBATCH --ntasks-per-node 15
#SBATCH --cpus-per-task 1
#SBATCH --nodes 10
#SBATCH -o slurm.%j.out         # STDOUT
#SBATCH -e slurm.%j.err         # STDERR

source /home/hpcschud/.bashrc

cd $SLURM_SUBMIT_DIR

mpirun -np 120 -- pimpleFoam -parallel > log.slurm_pimpleFoam 2>&1
